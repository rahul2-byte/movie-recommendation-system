import logging
import numpy as np
from scipy.sparse import csr_matrix
from typing import Tuple

from .config import ItemItemCFConfig
from .types import ItemSimilarityMatrix
from .utils import apply_implicit_weighting, l2_normalize_items

logger = logging.getLogger(__name__)


class ItemItemCFBuilder:
    """
    Builds sparse item–item similarity matrix using vectorized operations.
    """

    def __init__(self, config: ItemItemCFConfig) -> None:
        self.config = config

    def build(self, interactions: csr_matrix) -> ItemSimilarityMatrix:
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
        sim = mat.T @ mat  # sparse × sparse

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
        Keep only top-K similarities per row.
        """
        sim = sim.tocsr()
        for i in range(sim.shape[0]):
            row_start = sim.indptr[i]
            row_end = sim.indptr[i + 1]

            if row_end - row_start <= k:
                continue

            row_data = sim.data[row_start:row_end]
            top_k_idx = np.argpartition(row_data, -k)[-k:]

            mask = np.zeros_like(row_data, dtype=bool)
            mask[top_k_idx] = True

            sim.data[row_start:row_end] = row_data * mask

        sim.eliminate_zeros()
        return sim
