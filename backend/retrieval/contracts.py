"""Contracts for retrieval-domain candidate records."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalCandidate:
    """Candidate movie plus optional retrieval and ranking trace state."""

    tmdb_id: int
    retrieval_score: float = 0.0
    sources: list[str] = field(default_factory=list)
    source_scores: dict[str, float] = field(default_factory=dict)
    ranking_features: dict[str, Any] = field(default_factory=dict)
    ranking_score: float = 0.0

    @property
    def item_id(self) -> int:
        """Return the candidate's TMDB ID for compatibility with callers."""
        return self.tmdb_id
