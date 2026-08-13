"""Bundle-backed retrieval fusion and LightGBM ranking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np

from serving.candidate_fusion import collect_source_candidates, fuse_reciprocal_ranks
from serving.model_bundle import ModelBundle, ModelBundleError, load_model_bundle

_SOURCES = ("als", "item_graph", "two_tower", "content")
_SUPPORTED_FEATURES = {
    "retrieval_source_count",
    "retrieval_als_rank",
    "retrieval_als_score_normalized",
    "retrieval_item_graph_rank",
    "retrieval_item_graph_score_normalized",
    "retrieval_two_tower_rank",
    "retrieval_two_tower_score_normalized",
    "retrieval_content_rank",
    "retrieval_content_score_normalized",
    "candidate_train_interaction_count",
    "candidate_train_log_interaction_count",
}


def _content_text(field: str, value: object) -> str:
    if value is None:
        return ""
    if field == "release_year":
        value = value if value is not None else ""
        return f"year_{int(value)} decade_{int(value) // 10 * 10}" if value else ""
    if field == "runtime_minutes":
        return f"runtime_{int(value) // 15 * 15}" if value else ""
    if field in {"genres", "keywords", "top_cast"}:
        values = value if isinstance(value, list) else [value]
        return " ".join(
            f"{field}_{''.join(char if char.isalnum() else '_' for char in str(item).lower()).strip('_')}"
            for item in values
            if item
        )
    if field in {"director", "collection_name", "language", "country"}:
        normalized = "".join(
            char if char.isalnum() else "_" for char in str(value).lower()
        ).strip("_")
        return f"{field}_{normalized}" if normalized else ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    return str(value)


@dataclass(frozen=True)
class BundleRecommender:
    bundle: ModelBundle
    model: lgb.Booster
    feature_names: tuple[str, ...]
    popularity_counts: dict[int, float]
    candidate_limit: int
    rank_constant: int
    content_vectorizer: Any | None = None
    content_svd: Any | None = None
    content_fields: tuple[str, ...] = ()
    content_weights: dict[str, int] | None = None

    @classmethod
    def load(cls, root: Path | str) -> BundleRecommender:
        bundle = load_model_bundle(root)
        ranker_dir = bundle.root / "ranker"
        schema = json.loads((ranker_dir / "feature_schema.json").read_text())
        feature_names = tuple(schema.get("feature_names", ()))
        if not feature_names or set(feature_names) - _SUPPORTED_FEATURES:
            raise ModelBundleError("Ranker feature schema is unsupported by serving")
        popularity_path = ranker_dir / "popularity_counts.npz"
        if not popularity_path.is_file():
            raise ModelBundleError("Bundle lacks ranker popularity feature state")
        popularity = np.load(popularity_path, allow_pickle=False)
        ids = popularity["tmdb_ids"]
        counts = popularity["counts"]
        if ids.ndim != 1 or counts.ndim != 1 or len(ids) != len(counts):
            raise ModelBundleError("Bundle popularity feature state is invalid")
        content_dir = bundle.root / "retrievers" / "content"
        content_manifest = json.loads((content_dir / "manifest.json").read_text())
        return cls(
            bundle=bundle,
            model=lgb.Booster(model_file=str(ranker_dir / "model.txt")),
            feature_names=feature_names,
            popularity_counts={
                int(item_id): float(count)
                for item_id, count in zip(ids, counts, strict=True)
            },
            candidate_limit=int(bundle.manifest.get("candidate_limit", 300)),
            rank_constant=int(bundle.manifest.get("rrf_rank_constant", 60)),
            content_vectorizer=joblib.load(content_dir / "vectorizer.joblib"),
            content_svd=joblib.load(content_dir / "svd.joblib"),
            content_fields=tuple(content_manifest.get("text_fields", ())),
            content_weights={
                str(k): int(v)
                for k, v in content_manifest.get("field_weights", {}).items()
            },
        )

    def _content_retriever(self, seed_metadata: dict[int, dict[str, Any]]) -> Any:
        base = self.bundle.vector_retriever("content")
        if not seed_metadata:
            return base

        parent = self

        class ContentRetriever:
            def retrieve_one(self, seed_tmdb_id: int, top_k: int):
                if seed_tmdb_id in base.position_by_tmdb_id:
                    return base.retrieve_one(seed_tmdb_id, top_k)
                movie = seed_metadata.get(seed_tmdb_id)
                if (
                    movie is None
                    or parent.content_vectorizer is None
                    or parent.content_svd is None
                ):
                    return []
                values = {
                    **movie,
                    "release_year": movie.get("release_year", movie.get("year")),
                    "runtime_minutes": movie.get(
                        "runtime_minutes", movie.get("runtime")
                    ),
                }
                document = " ".join(
                    " ".join(
                        [_content_text(field, values.get(field))]
                        * int((parent.content_weights or {}).get(field, 1))
                    )
                    for field in parent.content_fields
                    if _content_text(field, values.get(field))
                )
                if not document.strip():
                    return []
                vector = parent.content_svd.transform(
                    parent.content_vectorizer.transform([document])
                ).astype(np.float32)
                norm = np.linalg.norm(vector)
                if norm == 0:
                    return []
                scores, positions = base.index.search(
                    vector / norm, min(base.index.ntotal, top_k)
                )
                return [
                    (int(base.tmdb_ids[int(position)]), float(score))
                    for score, position in zip(scores[0], positions[0], strict=True)
                    if int(position) >= 0
                ]

        return ContentRetriever()

    def recommend(
        self,
        seed_tmdb_ids: list[int],
        seed_metadata: dict[int, dict[str, Any]],
        *,
        top_n: int,
    ) -> list[tuple[int, float]]:
        seeds = list(
            dict.fromkeys(int(item_id) for item_id in seed_tmdb_ids if int(item_id) > 0)
        )
        if not seeds or top_n < 1:
            return []
        retrievers = {
            "als": self.bundle.vector_retriever("als"),
            "item_graph": self.bundle.item_graph,
            "two_tower": self.bundle.vector_retriever("two_tower"),
            "content": self._content_retriever(seed_metadata),
        }
        source_rows = {
            source: collect_source_candidates(
                retriever,
                seeds,
                int(getattr(retriever, "manifest", {}).get("per_seed_candidates", 200)),
            )
            for source, retriever in retrievers.items()
        }
        fused_candidates = fuse_reciprocal_ranks(
            source_rows, self.rank_constant, self.candidate_limit
        )
        candidate_ids = [item_id for item_id, _ in fused_candidates]
        if not candidate_ids:
            return []
        features = np.zeros(
            (len(candidate_ids), len(self.feature_names)), dtype=np.float32
        )
        for row, item_id in enumerate(candidate_ids):
            for column, name in enumerate(self.feature_names):
                if name == "retrieval_source_count":
                    features[row, column] = sum(
                        item_id in rows for rows in source_rows.values()
                    )
                elif name.endswith("_rank"):
                    source = name.removeprefix("retrieval_").removesuffix("_rank")
                    features[row, column] = source_rows.get(source, {}).get(item_id, 0)
                elif name.endswith("_score_normalized"):
                    source = name.removeprefix("retrieval_").removesuffix(
                        "_score_normalized"
                    )
                    rank = source_rows.get(source, {}).get(item_id, 0)
                    features[row, column] = 1.0 / rank if rank else 0.0
                elif name == "candidate_train_interaction_count":
                    features[row, column] = self.popularity_counts.get(item_id, 0.0)
                elif name == "candidate_train_log_interaction_count":
                    features[row, column] = np.log1p(
                        self.popularity_counts.get(item_id, 0.0)
                    )
        scores = self.model.predict(features)
        return sorted(
            (
                (item_id, float(score))
                for item_id, score in zip(candidate_ids, scores, strict=True)
            ),
            key=lambda value: (-value[1], value[0]),
        )[:top_n]
