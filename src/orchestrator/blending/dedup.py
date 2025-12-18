from typing import Dict, List

from ..contracts import Candidate


def deduplicate(candidates: List[Candidate]) -> List[Candidate]:
    """
    Merge duplicate items across retrievers.

    Preserves:
    - all source retrievers
    - all retriever-local scores
    """
    merged: Dict[int, Candidate] = {}

    for c in candidates:
        if c.item_id not in merged:
            merged[c.item_id] = c
        else:
            existing = merged[c.item_id]
            existing.sources.extend(c.sources)
            existing.scores.update(c.scores)

    return list(merged.values())
