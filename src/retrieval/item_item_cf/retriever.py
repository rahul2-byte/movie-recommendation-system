import logging
import numpy as np
from scipy.sparse import csr_matrix
from typing import Iterable

from .types import ItemSimilarityMatrix

logger = logging.getLogger(__name__)


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

        Args:
            user_history_items: item ids interacted by user
            user_history_weights: interaction strengths
            seen_items: items to filter out
            top_k: number of candidates

        Returns:
            Array of item ids
        """
        logger.debug("Retrieving ItemCF candidates")

        scores = np.zeros(self.similarity.shape[0], dtype=np.float32)

        for item, weight in zip(user_history_items, user_history_weights):
            scores += self.similarity[item].toarray().ravel() * weight

        scores[list(seen_items)] = 0.0

        if scores.sum() == 0.0:
            return np.array([], dtype=np.int64)

        top_items = np.argpartition(scores, -top_k)[-top_k:]
        top_items = top_items[np.argsort(-scores[top_items])]

        return top_items
