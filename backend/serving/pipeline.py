"""Request pipeline for the immutable local model bundle."""

from __future__ import annotations

from typing import Any, Protocol

from common.types import Query


class _Recommender(Protocol):
    def recommend(
        self,
        seed_tmdb_ids: list[int],
        seed_metadata: dict[int, dict[str, Any]],
        *,
        top_n: int,
    ) -> list[tuple[int, float]]: ...


class _MovieStore(Protocol):
    async def get_many_by_tmdb_ids(
        self, tmdb_ids: list[int]
    ) -> list[dict[str, Any]]: ...


class BundleRecommendationPipeline:
    """Fetch TMDB metadata around a compact local model bundle."""

    def __init__(self, recommender: _Recommender, movie_store: _MovieStore):
        self.recommender = recommender
        self.movie_store = movie_store

    async def recommend(
        self, query: Query, top_n: int = 20, request_id: str | None = None
    ) -> list[dict[str, Any]]:
        seeds = list(dict.fromkeys(query.seed_tmdb_ids))
        seed_movies = await self.movie_store.get_many_by_tmdb_ids(seeds)
        seed_metadata = {int(movie["tmdbId"]): movie for movie in seed_movies}
        ranked = self.recommender.recommend(seeds, seed_metadata, top_n=top_n * 2)
        movies = await self.movie_store.get_many_by_tmdb_ids(
            [item_id for item_id, _ in ranked]
        )
        by_id = {int(movie["tmdbId"]): movie for movie in movies}
        results = []
        seen = set(seeds)
        for item_id, score in ranked:
            if item_id in seen or item_id not in by_id:
                continue
            seen.add(item_id)
            results.append({**by_id[item_id], "score": score, "rating": score})
            if len(results) == top_n:
                break
        return results
