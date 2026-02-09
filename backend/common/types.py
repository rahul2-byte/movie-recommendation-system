from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Query:
    """
    Represents an inbound query to the recommendation system.
    """

    seed_movie_ids: List[int]
    # Future extension: could include user context, device type, etc.


@dataclass
class Candidate:
    """
    Represents a single recommendation candidate.
    This object is enriched as it passes through the pipeline.
    """

    movie_id: int
    score: float = 0.0

    # Traceability
    sources: List[str] = field(default_factory=list)  # e.g. ["two_tower", "als"]
    scores: Dict[str, float] = field(default_factory=dict)  # e.g. {"two_tower": 0.8}

    # Metadata (optional)
    features: Dict[str, Any] = field(default_factory=dict)
    rank_score: float = 0.0

    @property
    def item_id(self) -> int:
        return self.movie_id

