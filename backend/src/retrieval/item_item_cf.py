"""
Single-file Item–Item Collaborative Filtering (CF)

Pipeline:
    User–Item → (implicit weighting) → L2 normalize →
    Item–Item similarity → Top-K prune → Retrieval

Designed for sparse, large-scale recommender systems.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Tuple, Iterable

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize


# ============================================================
# Logging
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# Types
# ============================================================

UserId = int
ItemId = int
Score = float

UserItemMatrix = csr_matrix
ItemSimilarityMatrix = csr_matrix

ItemNeighbors = Dict[ItemId, Tuple[np.ndarray, np.ndarray]]


# ============================================================
# Configuration
# ============================================================

@dataclass(frozen=True)
class ItemItemCFConfig:
    top_k_per_item: int = 500
    implicit_alpha: float = 40.0
    min_interactions_per_item: int = 5
    use_implicit: bool = True
    dtype: str = "float32"


# ============================================================
# Utilities
# ============================================================

def apply_implicit_weighting(
    matrix: csr_matrix,
    alpha: float,
) -> csr_matrix:
    """
    Apply confidence weighting for implicit feedback.

    confidence = 1 + alpha * interaction
    """
    logger.info("Applying implicit confidence weighting")
    mat = matrix.copy()
    mat.data = 1.0 + alpha * mat.data
    return mat


def l2_normalize_items(matrix: csr_matrix) -> csr_matrix:
    """
    L2 normalize item vectors (columns).
    """
    logger.info("L2 normalizing item vectors")
    return normalize(matrix, norm="l2", axis=0)


# ============================================================
# Builder
# ============================================================

class ItemItemCFBuilder:
    """
    Builds sparse item–item similarity matrix using
    fully vectorized operations.
    """

    def __init__(self, config: ItemItemCFConfig) -> None:
        self.config = config

    def build(self, interactions: UserItemMatrix) -> ItemSimilarityMatrix:
        """
        Build item–item similarity matrix.

        Args:
            interactions: User–Item sparse matrix (CSR)

        Returns:
            Sparse Item–Item similarity matrix (CSR)
        """
        logger.info("Building Item–Item CF similarity matrix")

        mat = interactions.astype(self.config.dtype)

        if self.config.use_implicit:
            mat = apply_implicit_weighting(mat, self.config.implicit_alpha)

        mat = l2_normalize_items(mat)

        logger.info("Computing sparse item–item dot product")
        sim: csr_matrix = mat.T @ mat

        sim.setdiag(0.0)
        sim.eliminate_zeros()

        logger.info("Pruning top-K similarities per item")
        return self._top_k_prune(sim, self.config.top_k_per_item)

    @staticmethod
    def _top_k_prune(
        sim: csr_matrix,
        k: int,
    ) -> ItemSimilarityMatrix:
        """
        Keep only top-K similarities per item (row-wise).
        """
        sim = sim.tocsr()

        for i in range(sim.shape[0]):
            row_start = sim.indptr[i]
            row_end = sim.indptr[i + 1]

            nnz = row_end - row_start
            if nnz <= k:
                continue

            row_data = sim.data[row_start:row_end]

            top_k_idx = np.argpartition(row_data, -k)[-k:]
            mask = np.zeros_like(row_data, dtype=bool)
            mask[top_k_idx] = True

            sim.data[row_start:row_end] = row_data * mask

        sim.eliminate_zeros()
        return sim


# ============================================================
# Retriever
# ============================================================

class ItemItemCFRetriever:
    """
    Retrieves candidate items for a user using Item–Item CF.
    """

    def __init__(self, similarity: ItemSimilarityMatrix) -> None:
        self.similarity = similarity.tocsr()

    def retrieve(
        self,
        user_history_items: np.ndarray,
        user_history_weights: np.ndarray,
        seen_items: Iterable[int],
        top_k: int,
    ) -> np.ndarray:
        """
        Retrieve candidate items.

        Score aggregation:
            sum(sim(item_i, candidate_j) * weight_i)
        """
        logger.debug("Retrieving Item–Item CF candidates")

        scores = np.zeros(self.similarity.shape[0], dtype=np.float32)

        for item, weight in zip(user_history_items, user_history_weights):
            scores += self.similarity[item].toarray().ravel() * weight

        scores[list(seen_items)] = 0.0

        if scores.sum() == 0.0:
            return np.array([], dtype=np.int64)

        top_items = np.argpartition(scores, -top_k)[-top_k:]
        top_items = top_items[np.argsort(-scores[top_items])]

        return top_items
