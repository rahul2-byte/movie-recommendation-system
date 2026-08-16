"""Memory-bounded inputs and validation for leakage-safe ranker training."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pyarrow.parquet as pq
from data_pipeline.manifests import write_json
from evaluation.metrics import map_at_k, mrr_at_k, ndcg_at_k
from hashing import sha256

from training.ranking.config import RankingTrainingConfig


@dataclass(frozen=True)
class FeatureContract:
    """The versioned feature interface shared by training and validation."""

    schema_version: str
    dataset_version: str
    feature_names: tuple[str, ...]
    config_sha256: str
    code_sha256: str


@dataclass(frozen=True)
class PackedRankingData:
    """Disk-backed ranker inputs and their query grouping metadata."""

    output_dir: Path
    features_path: Path
    labels_path: Path
    groups_path: Path
    query_ids_path: Path
    feature_names: tuple[str, ...]
    row_count: int
    query_count: int
    feature_dtype: str
    query_id_dtype: str


@dataclass(frozen=True)
class RankerTrainingResult:
    """The immutable ranker artifact and its held-out validation comparison."""

    artifact_dir: Path
    manifest: dict[str, object]
    validation_metrics: dict[str, dict[str, float]]


def read_feature_contract(feature_dir: Path) -> FeatureContract:
    """Read the feature schema and manifest from one materialized directory."""
    schema_path = feature_dir / "feature_schema.json"
    manifest_path = feature_dir / "manifest.json"
    if not schema_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError(f"Feature artifact is incomplete: {feature_dir}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError(f"Feature artifact is not complete: {feature_dir}")
    names = schema.get("feature_names")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError(f"Feature schema has invalid feature_names: {schema_path}")
    contract = FeatureContract(
        schema_version=str(schema.get("schema_version", "")),
        dataset_version=str(schema.get("dataset_version", "")),
        feature_names=tuple(names),
        config_sha256=str(schema.get("config_sha256", "")),
        code_sha256=str(schema.get("code_sha256", "")),
    )
    if not all(
        [
            contract.schema_version,
            contract.dataset_version,
            contract.feature_names,
            contract.config_sha256,
            contract.code_sha256,
        ]
    ):
        raise ValueError(f"Feature schema is incomplete: {schema_path}")
    return contract


def validate_feature_compatibility(
    train_feature_dir: Path, validation_feature_dir: Path
) -> FeatureContract:
    """Reject train and validation directories with different contracts."""
    """Fail before training if feature definitions differ across partitions."""
    train = read_feature_contract(train_feature_dir.resolve())
    validation = read_feature_contract(validation_feature_dir.resolve())
    for field in (
        "schema_version",
        "dataset_version",
        "feature_names",
        "config_sha256",
        "code_sha256",
    ):
        if getattr(train, field) != getattr(validation, field):
            name = {
                "config_sha256": "feature_config_sha256",
                "code_sha256": "feature_code_sha256",
            }.get(field, field)
            raise ValueError(f"Train and validation differ in {name}")
    return train


def _packed_result(output_dir: Path, contract: FeatureContract) -> PackedRankingData:
    """Describe packed memmaps written for one feature contract."""
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files", {})
    feature_filename = str(files.get("features", "features.f32"))
    query_id_filename = str(files.get("query_ids", "query_ids.i64"))
    return PackedRankingData(
        output_dir=output_dir,
        features_path=output_dir / feature_filename,
        labels_path=output_dir / "labels.u8",
        groups_path=output_dir / "groups.npy",
        query_ids_path=output_dir / query_id_filename,
        feature_names=contract.feature_names,
        row_count=int(manifest["row_count"]),
        query_count=int(manifest["query_count"]),
        feature_dtype=str(
            manifest.get("storage_dtypes", {}).get("features", "float32")
        ),
        query_id_dtype=str(
            manifest.get("storage_dtypes", {}).get("query_ids", "int64")
        ),
    )


def _build_groups(query_ids: np.memmap, row_count: int) -> np.ndarray:
    """Build LightGBM query-group sizes from sorted query IDs."""
    if row_count < 1:
        raise ValueError("Ranking feature dataset has no rows")
    groups: list[int] = []
    previous_query: int | None = None
    open_group_size = 0
    chunk_size = 1_000_000
    for start in range(0, row_count, chunk_size):
        values = np.asarray(query_ids[start : min(start + chunk_size, row_count)])
        if np.any(values[1:] < values[:-1]):
            raise ValueError("Ranking query IDs are not monotonically ordered")
        for query_id, count in zip(
            np.unique(values, return_counts=True)[0],
            np.unique(values, return_counts=True)[1],
            strict=True,
        ):
            query = int(query_id)
            count = int(count)
            if previous_query is None:
                previous_query = query
                open_group_size = count
            elif query == previous_query:
                open_group_size += count
            else:
                if query < previous_query:
                    raise ValueError("Ranking query IDs are not monotonically ordered")
                groups.append(open_group_size)
                previous_query = query
                open_group_size = count
    groups.append(open_group_size)
    result = np.asarray(groups, dtype=np.int32)
    if int(result.sum()) != row_count:
        raise ValueError("Ranking groups do not sum to the feature row count")
    return result


def pack_ranking_features(
    feature_dir: Path,
    output_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> PackedRankingData:
    """Pack ordered Parquet features into resumable disk-backed NumPy arrays."""
    feature_dir = feature_dir.resolve()
    output_dir = output_dir.resolve()
    contract = read_feature_contract(feature_dir)
    source_path = feature_dir / "ranking_features.parquet"
    if not source_path.is_file():
        raise FileNotFoundError(f"Feature parquet is missing: {source_path}")
    source = pq.ParquetFile(source_path)
    row_count = int(source.metadata.num_rows)
    if row_count < 1:
        raise ValueError("Ranking feature dataset has no rows")
    expected = {
        "source_sha256": sha256(source_path),
        "schema_sha256": sha256(feature_dir / "feature_schema.json"),
        "feature_names": list(contract.feature_names),
        "row_count": row_count,
    }
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") == "complete" and all(
            manifest.get(key) == value for key, value in expected.items()
        ):
            return _packed_result(output_dir, contract)
        raise ValueError(f"Packed ranking output is incompatible: {output_dir}")

    work_dir = output_dir / ".work"
    state_path = work_dir / "state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if any(state.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Cannot resume incompatible packed output: {output_dir}")
        completed = int(state["completed_row_groups"])
        offset = int(state["row_offset"])
        mode = "r+"
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        state = {**expected, "completed_row_groups": 0, "row_offset": 0}
        completed = 0
        offset = 0
        mode = "w+"

    feature_count = len(contract.feature_names)
    feature_dtype = np.float16
    query_id_dtype = np.int32
    features = np.memmap(
        output_dir / "features.f16",
        dtype=feature_dtype,
        mode=mode,
        shape=(row_count, feature_count),
    )
    labels = np.memmap(
        output_dir / "labels.u8", dtype=np.uint8, mode=mode, shape=(row_count,)
    )
    query_ids = np.memmap(
        output_dir / "query_ids.i32",
        dtype=query_id_dtype,
        mode=mode,
        shape=(row_count,),
    )
    columns = ["query_index", "label", *contract.feature_names]
    for row_group in range(completed, source.metadata.num_row_groups):
        table = source.read_row_group(row_group, columns=columns)
        size = len(table)
        stop = offset + size
        source_query_ids = table["query_index"].to_numpy()
        if source_query_ids.size and (
            np.min(source_query_ids) < np.iinfo(query_id_dtype).min
            or np.max(source_query_ids) > np.iinfo(query_id_dtype).max
        ):
            raise ValueError("Ranking query IDs exceed int32 storage range")
        query_ids[offset:stop] = source_query_ids
        labels[offset:stop] = table["label"].to_numpy()
        feature_values = np.column_stack(
            [table[name].to_numpy() for name in contract.feature_names]
        ).astype(np.float32, copy=False)
        if (
            not np.isfinite(feature_values).all()
            or np.max(np.abs(feature_values), initial=0.0) > np.finfo(feature_dtype).max
        ):
            raise ValueError("Ranking features cannot be represented as float16")
        features[offset:stop] = feature_values.astype(feature_dtype)
        features.flush()
        labels.flush()
        query_ids.flush()
        offset = stop
        state["completed_row_groups"] = row_group + 1
        state["row_offset"] = offset
        write_json(state_path, state)
        if progress_callback is not None:
            progress_callback(row_group + 1, source.metadata.num_row_groups)
    if offset != row_count:
        raise ValueError("Packed ranking rows do not match Parquet metadata")

    groups = _build_groups(query_ids, row_count)
    groups_path = output_dir / "groups.npy"
    np.save(groups_path, groups)
    write_json(
        manifest_path,
        {
            "status": "complete",
            **expected,
            "query_count": int(len(groups)),
            "files": {
                "features": "features.f16",
                "labels": "labels.u8",
                "query_ids": "query_ids.i32",
                "groups": "groups.npy",
            },
            "storage_dtypes": {"features": "float16", "query_ids": "int32"},
        },
    )
    return _packed_result(output_dir, contract)


def _open_packed(data: PackedRankingData) -> tuple[np.memmap, np.memmap, np.ndarray]:
    """Open packed feature, label, and query-group arrays read-only."""
    features = np.memmap(
        data.features_path,
        dtype=np.dtype(data.feature_dtype),
        mode="r",
        shape=(data.row_count, len(data.feature_names)),
    )
    labels = np.memmap(
        data.labels_path, dtype=np.uint8, mode="r", shape=(data.row_count,)
    )
    groups = np.load(data.groups_path)
    if int(groups.sum()) != data.row_count or len(groups) != data.query_count:
        raise ValueError(f"Packed ranking groups are invalid: {data.output_dir}")
    return features, labels, groups


def _mean_ranking_metrics(
    labels: np.ndarray, scores: np.ndarray, groups: np.ndarray, ks: tuple[int, ...]
) -> dict[str, float]:
    """Compute mean top-k ranking metrics over query groups."""
    totals = {f"ndcg_at_{k}": 0.0 for k in ks}
    totals["map_at_10"] = 0.0
    totals["mrr_at_10"] = 0.0
    start = 0
    for group_size in groups:
        stop = start + int(group_size)
        order = np.argsort(-scores[start:stop], kind="stable")
        ranked_labels = labels[start:stop][order]
        for k in ks:
            totals[f"ndcg_at_{k}"] += ndcg_at_k(ranked_labels, k)
        totals["map_at_10"] += map_at_k(ranked_labels, 10)
        totals["mrr_at_10"] += mrr_at_k(ranked_labels, 10)
        start = stop
    return {key: value / len(groups) for key, value in totals.items()}


def _rrf_scores(
    features: np.ndarray, feature_names: tuple[str, ...], rank_constant: int
) -> np.ndarray:
    """Compute retrieval-only reciprocal-rank baseline scores."""
    scores = np.zeros(len(features), dtype=np.float32)
    for index, name in enumerate(feature_names):
        if not name.startswith("retrieval_") or not name.endswith("_rank"):
            continue
        ranks = features[:, index]
        scores += np.divide(
            1.0,
            rank_constant + ranks,
            out=np.zeros_like(ranks, dtype=np.float32),
            where=ranks > 0,
        )
    return scores


def _training_progress(
    callback: Callable[[int, int], None] | None, total: int
) -> Callable[[object], None]:
    """Adapt progress callbacks to LightGBM's callback protocol."""

    def report(environment: object) -> None:
        """Forward one LightGBM iteration update to the caller."""
        if callback is not None:
            callback(min(environment.iteration + 1, total), total)

    report.order = 20
    return report


def train_ranker(
    train: PackedRankingData,
    validation: PackedRankingData,
    contract: FeatureContract,
    config: RankingTrainingConfig,
    artifact_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> RankerTrainingResult:
    """Fit LambdaRank on inner history and report held-out validation only."""
    if (
        train.feature_names != contract.feature_names
        or validation.feature_names != contract.feature_names
    ):
        raise ValueError(
            "Packed ranking feature names do not match the feature contract"
        )
    train_features, train_labels, train_groups = _open_packed(train)
    validation_features, validation_labels, validation_groups = _open_packed(validation)
    parameters = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_at": list(config.ndcg_ks),
        "learning_rate": config.learning_rate,
        "num_leaves": config.num_leaves,
        "min_data_in_leaf": config.min_data_in_leaf,
        "lambda_l2": config.lambda_l2,
        "seed": config.random_seed,
        "num_threads": config.num_threads,
        "verbosity": -1,
    }
    model = lgb.train(
        parameters,
        lgb.Dataset(
            train_features,
            label=train_labels,
            group=train_groups,
            feature_name=list(contract.feature_names),
            free_raw_data=False,
        ),
        num_boost_round=config.num_boost_round,
        valid_sets=[
            lgb.Dataset(
                validation_features,
                label=validation_labels,
                group=validation_groups,
                feature_name=list(contract.feature_names),
                free_raw_data=False,
            )
        ],
        valid_names=["validation"],
        callbacks=[
            lgb.early_stopping(config.early_stopping_rounds, verbose=False),
            _training_progress(progress_callback, config.num_boost_round),
        ],
    )
    best_iteration = model.best_iteration or model.current_iteration()
    validation_scores = model.predict(validation_features, num_iteration=best_iteration)
    popularity_name = "candidate_train_interaction_count"
    if popularity_name not in contract.feature_names:
        raise ValueError(f"Ranking feature schema is missing {popularity_name}")
    popularity_scores = validation_features[
        :, contract.feature_names.index(popularity_name)
    ]
    validation_metrics = {
        "popularity": _mean_ranking_metrics(
            validation_labels, popularity_scores, validation_groups, config.ndcg_ks
        ),
        "rrf": _mean_ranking_metrics(
            validation_labels,
            _rrf_scores(
                validation_features, contract.feature_names, config.rrf_rank_constant
            ),
            validation_groups,
            config.ndcg_ks,
        ),
        "lightgbm": _mean_ranking_metrics(
            validation_labels, validation_scores, validation_groups, config.ndcg_ks
        ),
    }
    artifact_dir = artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.txt"
    model.save_model(str(model_path), num_iteration=best_iteration)
    schema_path = artifact_dir / "feature_schema.json"
    write_json(
        schema_path,
        {
            "schema_version": contract.schema_version,
            "dataset_version": contract.dataset_version,
            "feature_names": list(contract.feature_names),
            "config_sha256": contract.config_sha256,
            "code_sha256": contract.code_sha256,
        },
    )
    metrics_path = artifact_dir / "validation_metrics.json"
    write_json(metrics_path, validation_metrics)
    manifest = {
        "status": "complete",
        "model_type": "lightgbm_lambdarank",
        "random_seed": config.random_seed,
        "best_iteration": best_iteration,
        "feature_names": list(contract.feature_names),
        "feature_schema_version": contract.schema_version,
        "dataset_version": contract.dataset_version,
        "feature_config_sha256": contract.config_sha256,
        "feature_code_sha256": contract.code_sha256,
        "training_config_sha256": sha256(config.path),
        "train_rows": train.row_count,
        "train_query_count": train.query_count,
        "validation_rows": validation.row_count,
        "validation_query_count": validation.query_count,
        "validation_metrics": validation_metrics,
        "artifact_sha256": {
            "model": sha256(model_path),
            "feature_schema": sha256(schema_path),
            "validation_metrics": sha256(metrics_path),
        },
    }
    write_json(artifact_dir / "manifest.json", manifest)
    return RankerTrainingResult(artifact_dir, manifest, validation_metrics)


def evaluate_ranker(
    artifact_dir: Path,
    evaluation: PackedRankingData,
    contract: FeatureContract,
    config: RankingTrainingConfig,
) -> dict[str, dict[str, float]]:
    """Score an immutable held-out feature artifact with a compatible ranker."""
    artifact_dir = artifact_dir.resolve()
    manifest_path = artifact_dir / "manifest.json"
    model_path = artifact_dir / "model.txt"
    if not manifest_path.is_file() or not model_path.is_file():
        raise FileNotFoundError(f"Ranker artifact is incomplete: {artifact_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError(f"Ranker artifact is not complete: {artifact_dir}")
    if (
        tuple(manifest.get("feature_names", ())) != contract.feature_names
        or manifest.get("feature_schema_version") != contract.schema_version
        or manifest.get("dataset_version") != contract.dataset_version
    ):
        raise ValueError("Ranker artifact is incompatible with evaluation features")
    if evaluation.feature_names != contract.feature_names:
        raise ValueError("Evaluation feature names do not match the feature contract")
    features, labels, groups = _open_packed(evaluation)
    model = lgb.Booster(model_file=str(model_path))
    scores = model.predict(features)
    popularity_name = "candidate_train_interaction_count"
    if popularity_name not in contract.feature_names:
        raise ValueError(f"Ranking feature schema is missing {popularity_name}")
    popularity_scores = features[:, contract.feature_names.index(popularity_name)]
    return {
        "popularity": _mean_ranking_metrics(
            labels, popularity_scores, groups, config.ndcg_ks
        ),
        "rrf": _mean_ranking_metrics(
            labels,
            _rrf_scores(features, contract.feature_names, config.rrf_rank_constant),
            groups,
            config.ndcg_ks,
        ),
        "lightgbm": _mean_ranking_metrics(labels, scores, groups, config.ndcg_ks),
    }
