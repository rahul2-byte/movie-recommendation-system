import logging
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)


def apply_implicit_weighting(
    matrix: csr_matrix,
    alpha: float,
) -> csr_matrix:
    """
    Apply confidence weighting for implicit feedback.

    confidence = 1 + alpha * interaction
    """
    logger.info("Applying implicit confidence weighting")
    matrix = matrix.copy()
    matrix.data = 1.0 + alpha * matrix.data
    return matrix


def l2_normalize_items(matrix: csr_matrix) -> csr_matrix:
    """
    L2 normalize item vectors (columns).
    """
    logger.info("L2 normalizing item vectors")
    return normalize(matrix, norm="l2", axis=0)
