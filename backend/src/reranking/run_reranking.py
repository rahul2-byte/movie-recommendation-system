import logging
from pathlib import Path
from typing import List, Dict

import pandas as pd
import lightgbm as lgb

from reranking.reranker import Reranker
from ranking.config import (
    DATA_PATH,
    MODEL_OUTPUT_PATH,
    DROP_COLS,
    GROUP_COL,
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# -------------------------------------------------
# CONFIG
# -------------------------------------------------
TOP_K_INPUT = 200   # candidates passed into reranker
TOP_K_OUTPUT = 20   # final slate per user


# -------------------------------------------------
# LOAD RANKING DATA + MODEL
# -------------------------------------------------
def load_ranked_candidates() -> pd.DataFrame:
    LOGGER.info("Loading ranking features")
    df = pd.read_parquet(DATA_PATH)

    df = df.sort_values(GROUP_COL)

    LOGGER.info("Loading LightGBM ranker")
    model = lgb.Booster(model_file=MODEL_OUTPUT_PATH)

    features = df.drop(columns=DROP_COLS)
    df["score"] = model.predict(features)

    return df


# -------------------------------------------------
# USER-LEVEL RE-RANKING
# -------------------------------------------------
def rerank_per_user(df: pd.DataFrame) -> Dict[int, List[dict]]:
    reranker = Reranker()
    final_results: Dict[int, List[dict]] = {}

    for user_id, user_df in df.groupby(GROUP_COL, sort=False):
        # Take top-N ranked candidates
        top_candidates = (
            user_df
            .sort_values("score", ascending=False)
            .head(TOP_K_INPUT)
        )

        ranked_items = [
            {
                "item_id": int(row["item_id"]),
                "score": float(row["score"]),
                # Optional metadata (must exist in features or joined table)
                "genres": row.get("genres", []),
                "franchise": row.get("franchise"),
                "release_timestamp": row.get("release_timestamp"),
            }
            for _, row in top_candidates.iterrows()
        ]

        final_items = reranker.rerank(ranked_items)
        final_results[int(user_id)] = final_items

    return final_results


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    ranked_df = load_ranked_candidates()

    LOGGER.info("Running re-ranking (diversity + freshness)")
    final_slates = rerank_per_user(ranked_df)

    # Example: inspect one user
    sample_user = next(iter(final_slates))
    LOGGER.info("Sample re-ranked slate for user %s:", sample_user)
    for item in final_slates[sample_user][:TOP_K_OUTPUT]:
        LOGGER.info(item)
