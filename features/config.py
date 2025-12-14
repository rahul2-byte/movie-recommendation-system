from pathlib import Path
from typing import Final

# ---------------------------------------------------------
# Base Directories
# ---------------------------------------------------------
BASE_DIR: Final[Path] = Path.cwd()

RAW_DIR: Final[Path] = BASE_DIR / "data" / "raw"
PROCESSED_DIR: Final[Path] = BASE_DIR / "data" / "processed"
FEATURE_DIR: Final[Path] = PROCESSED_DIR / "features"
MODELS_DIR: Final[Path] = BASE_DIR / "models"

# Ensure feature directory exists
FEATURE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Raw Data File Paths
# (MovieLens-style defaults; override via CLI or pipeline)
# ---------------------------------------------------------
RATINGS_CSV: Final[str] = str(RAW_DIR / "ratings.csv")
MOVIES_CSV: Final[str] = str(RAW_DIR / "movies.csv")
TAGS_CSV: Final[str]   = str(RAW_DIR / "tags.csv")     # NEW


# ---------------------------------------------------------
# Feature Output Files
# ---------------------------------------------------------
USER_FEATURES_PQ: Final[str] = str(FEATURE_DIR / "user_features.parquet")
ITEM_FEATURES_PQ: Final[str] = str(FEATURE_DIR / "item_features.parquet")

# If needed later (keeping for extensibility):
TAGS_FEATURES_PQ: Final[str] = str(FEATURE_DIR / "tag_features.parquet")


# ---------------------------------------------------------
# System Defaults
# ---------------------------------------------------------
DEFAULT_DTYPE: Final[str] = "float32"
INT_DTYPE: Final[str] = "int32"

# Convert object → category when unique values / total rows <= threshold
CATEGORY_MAX_UNIQUE_FOR_CAT: Final[float] = 0.5
