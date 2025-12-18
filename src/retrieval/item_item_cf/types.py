from typing import Dict, List, Tuple
import numpy as np
from scipy.sparse import csr_matrix

UserId = int
ItemId = int
Score = float

UserItemMatrix = csr_matrix
ItemSimilarityMatrix = csr_matrix

ItemNeighbors = Dict[ItemId, Tuple[np.ndarray, np.ndarray]]
