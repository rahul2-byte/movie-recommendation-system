from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Candidate:
    """
    A recall candidate passed to the ranking layer.

    - item_id: external item identifier
    - sources: retrievers that surfaced this item
    - scores: retriever-local normalized scores
    """
    item_id: int
    sources: List[str]
    scores: Dict[str, float]
