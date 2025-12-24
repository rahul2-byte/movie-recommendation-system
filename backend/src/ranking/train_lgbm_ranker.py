import logging
from pathlib import Path
from typing import Tuple

import lightgbm as lgb
import pandas as pd
import numpy as np

from ranking.config import (
    DATA_PATH,
    MODEL_OUTPUT_PATH,
    LABEL_COL,
    GROUP_COL,
    DROP_COLS,
    SEED,
    N_ESTIMATORS,
    LEARNING_RATE,
    NUM_LEAVES,
    MAX_DEPTH,
    EVAL_AT,
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def load_data() -> Tuple[pd.DataFrame, pd.Series, np.ndarray]:
    LOGGER.info("Loading ranking features")
    df = pd.read_parquet(DATA_PATH)

    # Sort by user to form proper groups
    df = df.sort_values(GROUP_COL)

    y = df[LABEL_COL].astype(np.int8)

    X = df.drop(columns=DROP_COLS)

    # group sizes per user
    group_sizes = (
        df.groupby(GROUP_COL, sort=False)
        .size()
        .values
    )

    LOGGER.info(
        "Loaded data | rows=%d | features=%d | users=%d",
        len(df),
        X.shape[1],
        len(group_sizes),
    )

    return X, y, group_sizes


def train_lambdarank(
    X: pd.DataFrame,
    y: pd.Series,
    group_sizes: np.ndarray,
) -> lgb.Booster:
    LOGGER.info("Training LightGBM LambdaRank")

    train_set = lgb.Dataset(
        X,
        label=y,
        group=group_sizes,
        free_raw_data=False,
    )

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_eval_at": EVAL_AT,
        "learning_rate": LEARNING_RATE,
        "num_leaves": NUM_LEAVES,
        "max_depth": MAX_DEPTH,
        "min_data_in_leaf": 50,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "verbosity": -1,
        "seed": SEED,
    }

    model = lgb.train(
        params=params,
        train_set=train_set,
        num_boost_round=N_ESTIMATORS,
    )

    return model


def save_model(model: lgb.Booster) -> None:
    Path(MODEL_OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_OUTPUT_PATH)
    LOGGER.info("Model saved to %s", MODEL_OUTPUT_PATH)


if __name__ == "__main__":
    X, y, group_sizes = load_data()
    model = train_lambdarank(X, y, group_sizes)
    save_model(model)
