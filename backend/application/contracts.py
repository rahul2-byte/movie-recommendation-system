"""Contracts exchanged by the application recommendation workflow."""

from dataclasses import dataclass


@dataclass
class RecommendationQuery:
    """User-selected seed movies used to generate recommendations."""

    seed_tmdb_ids: list[int]
