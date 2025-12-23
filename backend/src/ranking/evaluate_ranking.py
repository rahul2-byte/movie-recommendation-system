import lightgbm as lgb
import pandas as pd
import numpy as np

from ranking.config import DATA_PATH, MODEL_OUTPUT_PATH, LABEL_COL, GROUP_COL, DROP_COLS


def evaluate_ndcg():
    df = pd.read_parquet(DATA_PATH).sort_values(GROUP_COL)

    y_true = df[LABEL_COL].values
    X = df.drop(columns=DROP_COLS)

    model = lgb.Booster(model_file=MODEL_OUTPUT_PATH)
    scores = model.predict(X)

    df["score"] = scores

    # Example: inspect one user
    user_id = df[GROUP_COL].iloc[0]
    print(df[df[GROUP_COL] == user_id][["item_id", "label", "score"]]
            .sort_values("score", ascending=False)
            .head(10))


if __name__ == "__main__":
    evaluate_ndcg()
