from collections import defaultdict
from typing import Dict, List


def can_add_item(
    item: dict,
    genre_counts: Dict[str, int],
    franchise_counts: Dict[str, int],
    max_per_genre: int,
    max_per_franchise: int,
) -> bool:
    for g in item.get("genres", []):
        if genre_counts[g] >= max_per_genre:
            return False

    franchise = item.get("franchise")
    if franchise and franchise_counts[franchise] >= max_per_franchise:
        return False

    return True
