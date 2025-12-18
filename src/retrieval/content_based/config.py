from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class TfidfConfig:
    # Vectorizer
    max_features: int = 100_000
    min_df: int = 5
    ngram_range: Tuple[int, int] = (1, 2)
    dtype: str = "float32"

    # Columns
    item_id_col: str = "movieId"
    title_col: str = "title"
    tag_col: str = "tag"

    embedding_dim: int = 128

    # Output
    artifact_dir: Path = Path("models/content_based")
