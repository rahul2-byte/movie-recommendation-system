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
        refresh_seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return up to ``top_n`` ranked, metadata-enriched movie records."""
        ranked_candidate_scores = await self.rank_candidates(
            seed_tmdb_ids,
            top_n=top_n,
            refresh_seed=refresh_seed,
        )
        recommendations, _ = await self.materialize_candidates(
            ranked_candidate_scores,
            offset=0,
            page_size=top_n,
        )
        return recommendations

    async def rank_candidates(
        self,
        seed_tmdb_ids: list[int],
        top_n: int,
        refresh_seed: int | None = None,
    ) -> list[tuple[int, float]]:
        """Rank candidates once so display pages can be enriched on demand."""
        unique_seed_tmdb_ids = list(dict.fromkeys(seed_tmdb_ids))
        seed_movies = await self.movie_store.get_many(unique_seed_tmdb_ids)
        seed_metadata = {int(movie["tmdbId"]): movie for movie in seed_movies}
        ranked_candidate_scores = self.recommender.recommend(
            unique_seed_tmdb_ids,
            seed_metadata,
            top_n=max(top_n + 8, top_n * 2),
        )
        if refresh_seed is not None:
            ranked_candidate_scores = list(ranked_candidate_scores)
            if ranked_candidate_scores:
                offset = refresh_seed % len(ranked_candidate_scores)
                ranked_candidate_scores = (
                    ranked_candidate_scores[offset:] + ranked_candidate_scores[:offset]
                )
        seen_tmdb_ids = set(unique_seed_tmdb_ids)
        candidates = []
        for item_id, score in ranked_candidate_scores:
            if item_id in seen_tmdb_ids:
                continue
            seen_tmdb_ids.add(item_id)
            candidates.append((item_id, score))
            if len(candidates) == top_n:
                break
        return candidates

    async def materialize_candidates(
        self,
        ranked_candidate_scores: list[tuple[int, float]],
        offset: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int | None]:
        """Enrich a page, skipping records that no longer have a poster."""
        recommendations = []
        cursor = offset
        while (
            cursor < len(ranked_candidate_scores) and len(recommendations) < page_size
        ):
            chunk = ranked_candidate_scores[cursor : cursor + page_size]
            movies = await self.movie_store.get_many([item_id for item_id, _ in chunk])
            movies_by_tmdb_id = {
                int(movie["tmdbId"]): movie
                for movie in movies
                if "posterUrl" not in movie or movie.get("posterUrl")
            }
            for item_id, score in chunk:
                movie = movies_by_tmdb_id.get(item_id)
                if movie is not None:
                    recommendations.append({**movie, "rankScore": score})
                    if len(recommendations) == page_size:
                        break
            cursor += len(chunk)
        return recommendations, cursor if cursor < len(
            ranked_candidate_scores
        ) else None
