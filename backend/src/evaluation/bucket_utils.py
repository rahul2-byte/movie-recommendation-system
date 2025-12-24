from typing import Dict


def item_popularity_buckets(
    item_interaction_counts: Dict[int, int]
) -> Dict[int, str]:
    buckets = {}
    for item_id, cnt in item_interaction_counts.items():
        if cnt == 0:
            buckets[item_id] = "cold"
        elif cnt <= 10:
            buckets[item_id] = "warm"
        else:
            buckets[item_id] = "hot"
    return buckets
