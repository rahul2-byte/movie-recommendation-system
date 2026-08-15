"""Request pipeline for the immutable local model bundle."""

from __future__ import annotations

from typing import Any, Protocol


class _Recommender(Protocol):
    """Minimal recommender contract required by application orchestration."""

    def recommend(
        self,
        seed_tmdb_ids: list[int],
        seed_metadata: dict[int, dict[str, Any]],
        *,
        top_n: int,
    ) -> list[tuple[int, float]]:
        """Return ranked candidate IDs and scores for the seed set."""
        ...


class _MovieStore(Protocol):
    """Minimal metadata contract required after model ranking."""

    async def get_many(self, tmdb_ids: list[int]) -> list[dict[str, Any]]:
        """Load display metadata for a batch of TMDB IDs."""
        ...


class BundleRecommendationPipeline:
    """Generate recommendations and enrich them from the metadata store.

    Retrieval and ranking stay local to the immutable bundle. Seed movies are
    never returned as recommendations.
    """

    def __init__(self, recommender: _Recommender, movie_store: _MovieStore):
        """Bind model-ranking and metadata-enrichment dependencies."""
        self.recommender = recommender
        self.movie_store = movie_store

    async def recommend(
        self,
        seed_tmdb_ids: list[int],
        top_n: int = 20,
    ) -> list[dict[str, Any]]:
        """Return up to ``top_n`` ranked, metadata-enriched movie records."""
        # Metadata enrichment is downstream of ranking. A lookup failure drops
        # one display record without changing the model candidate set or
        # failing the entire recommendation request.
        unique_seed_tmdb_ids = list(dict.fromkeys(seed_tmdb_ids))
        seed_movies = await self.movie_store.get_many(unique_seed_tmdb_ids)
        seed_metadata = {int(movie["tmdbId"]): movie for movie in seed_movies}
        ranked_candidate_scores = self.recommender.recommend(
            unique_seed_tmdb_ids, seed_metadata, top_n=top_n * 2
        )
        candidate_movies = await self.movie_store.get_many(
            [item_id for item_id, _ in ranked_candidate_scores]
        )
        movies_by_tmdb_id = {int(movie["tmdbId"]): movie for movie in candidate_movies}
        recommendations = []
        seen_tmdb_ids = set(unique_seed_tmdb_ids)
        for item_id, score in ranked_candidate_scores:
            if item_id in seen_tmdb_ids or item_id not in movies_by_tmdb_id:
                continue
            seen_tmdb_ids.add(item_id)
            recommendations.append(
                {**movies_by_tmdb_id[item_id], "score": score, "rating": score}
            )
            if len(recommendations) == top_n:
                break
        return recommendations
