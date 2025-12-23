from typing import List

# -------------------------------
# Data
# -------------------------------
DATA_PATH = "data/processed/ranking_features.parquet"
MODEL_OUTPUT_PATH = "models/ranker/lgbm_lambdarank.txt"

# -------------------------------
# Columns
# -------------------------------
LABEL_COL = "label"
GROUP_COL = "user_id"

# Exclude identifiers & label
DROP_COLS: List[str] = [
    "user_id",
    "item_id",
    "label",
]

# -------------------------------
# Training
# -------------------------------
SEED = 42
N_ESTIMATORS = 500
LEARNING_RATE = 0.05
NUM_LEAVES = 64
MAX_DEPTH = -1

EVAL_AT = [10, 50]
