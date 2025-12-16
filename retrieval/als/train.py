"""
ALS Training + Embedding Export (Production-Grade)

Responsibilities:
- Train implicit-feedback ALS
- Export FAISS-ready item embeddings
- Persist item_id_map + metadata
- NO indexing
- NO retrieval logic

Output contract:
models/als/
    - item_embeddings.npy
    - item_id_map.json
    - metadata.json
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logger = logging.getLogger("als.train")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ---------------------------------------------------------
# Config
# ---------------------------------------------------------
@dataclass(frozen=True)
class ALSConfig:
    factors: int = 128
    regularization: float = 0.05
    iterations: int = 20
    alpha: float = 40.0
    use_gpu: bool = False
    dtype: np.dtype = np.float32


# ---------------------------------------------------------
# Trainer
# ---------------------------------------------------------
class ALSModelTrainer:
    def __init__(self, config: ALSConfig) -> None:
        self.config = config
        self.model: Optional[AlternatingLeastSquares] = None

    @staticmethod
    def build_interaction_matrix(
        user_idx: np.ndarray,
        item_idx: np.ndarray,
        values: np.ndarray,
        num_users: int,
        num_items: int,
        dtype: np.dtype,
    ) -> sp.csr_matrix:
        logger.info("Building CSR interaction matrix")

        mat = sp.coo_matrix(
            (values.astype(dtype), (user_idx, item_idx)),
            shape=(num_users, num_items),
        ).tocsr()

        mat.sum_duplicates()
        mat.eliminate_zeros()
        return mat

    def train(self, interactions: sp.csr_matrix) -> None:
        logger.info("Training ALS model")

        self.model = AlternatingLeastSquares(
            factors=self.config.factors,
            regularization=self.config.regularization,
            iterations=self.config.iterations,
            use_gpu=self.config.use_gpu,
            dtype=self.config.dtype,
        )

        # implicit expects item-user
        self.model.fit(interactions.T * self.config.alpha)

        logger.info("ALS training complete")

    def save(
        self,
        output_dir: Path,
        item_id_map: List[int],
    ) -> None:
        if self.model is None:
            raise RuntimeError("Model must be trained before saving")

        output_dir.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------
        # Item embeddings (FAISS-ready)
        # -------------------------------------------------
        item_embeddings = self.model.item_factors.astype(np.float32)
        item_embeddings = np.ascontiguousarray(item_embeddings)

        np.save(output_dir / "item_embeddings.npy", item_embeddings)

        # -------------------------------------------------
        # Item ID map (CRITICAL)
        # index -> original movieId
        # -------------------------------------------------
        with open(output_dir / "item_id_map.json", "w") as f:
            json.dump(
                {int(item_id): idx for idx, item_id in enumerate(item_id_map)},
                f,
            )

        # -------------------------------------------------
        # Metadata
        # -------------------------------------------------
        metadata = {
            "model": "als",
            "num_items": int(item_embeddings.shape[0]),
            "embedding_dim": int(item_embeddings.shape[1]),
            "dtype": "float32",
            "normalized": False,  # ALS uses dot-product
            "alpha": self.config.alpha,
            "factors": self.config.factors,
            "regularization": self.config.regularization,
        }

        with open(output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("ALS artifacts written to %s", output_dir)


# ---------------------------------------------------------
# Example Usage (Pipeline Entry Point)
# ---------------------------------------------------------
def train_and_export_als(
    interactions_df: pd.DataFrame,
    output_dir: str,
    config: ALSConfig,
) -> None:
    """
    interactions_df columns required:
        - userId
        - movieId
        - value (implicit signal)
    """

    # -------------------------------------------------
    # ID remapping (SOURCE OF TRUTH)
    # -------------------------------------------------
    user_codes = pd.Categorical(interactions_df["userId"])
    item_codes = pd.Categorical(interactions_df["movieId"])

    interactions_df["user_idx"] = user_codes.codes.astype("int64")
    interactions_df["item_idx"] = item_codes.codes.astype("int64")

    item_id_map = item_codes.categories.tolist()

    num_users = len(user_codes.categories)
    num_items = len(item_codes.categories)

    # -------------------------------------------------
    # Interaction matrix
    # -------------------------------------------------
    X = ALSModelTrainer.build_interaction_matrix(
        user_idx=interactions_df["user_idx"].values,
        item_idx=interactions_df["item_idx"].values,
        values=interactions_df["value"].values,
        num_users=num_users,
        num_items=num_items,
        dtype=config.dtype,
    )

    # -------------------------------------------------
    # Train + Export
    # -------------------------------------------------
    trainer = ALSModelTrainer(config)
    trainer.train(X)
    trainer.save(Path(output_dir), item_id_map)


# ---------------------------------------------------------
# End of file
# ---------------------------------------------------------
