from typing import Iterable, List, Set

from ..contracts import Candidate


def filter_seen_items(
    candidates: List[Candidate],
    seen_item_ids: Iterable[int],
) -> List[Candidate]:
    """
    Remove items already seen by the user.
    """
    seen: Set[int] = set(seen_item_ids)

    return [
        c for c in candidates
        if c.item_id not in seen
    ]
