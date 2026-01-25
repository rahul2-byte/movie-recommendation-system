from typing import Dict, List
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class RecallCandidate:
    movie_id: int
    recall_score: float
    source: str # "als", "two_tower", "item_cf", "content"

@dataclass
class UserEmbedding:
    vector: np.ndarray
    source: str  # "seed_mean"

@dataclass
class Candidate:
    item_id: int
    sources: List[str]
    scores: Dict[str, float]
