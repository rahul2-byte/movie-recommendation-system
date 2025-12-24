from typing import Set, List, Dict
import numpy as np


def recall_at_k(
    relevant_items: Set[int],
    retrieved_items: List[int],
    k: int
) -> float:
    if not relevant_items:
        return 0.0
    retrieved_k = set(retrieved_items[:k])
    return len(retrieved_k & relevant_items) / len(relevant_items)


def hitrate_at_k(
    relevant_items: Set[int],
    retrieved_items: List[int],
    k: int
) -> float:
    if not relevant_items:
        return 0.0
    return float(len(set(retrieved_items[:k]) & relevant_items) > 0)


def catalog_coverage(
    retrieved_items: Set[int],
    total_items: int
) -> float:
    return len(retrieved_items) / total_items
