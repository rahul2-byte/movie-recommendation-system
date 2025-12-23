from typing import List

from ..contracts import Candidate


def validate_candidates(candidates: List[Candidate]) -> None:
    """
    Defensive checks to catch silent bugs early.
    """
    for c in candidates:
        assert isinstance(c.item_id, int)
        assert c.sources
        assert c.scores
