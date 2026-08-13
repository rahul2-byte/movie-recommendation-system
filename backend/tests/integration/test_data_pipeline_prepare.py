from __future__ import annotations

from pathlib import Path

import pandas as pd
from data_pipeline.config import load_config
from data_pipeline.prepare import prepare_dataset


def _write_config(path: Path) -> None:
    path.write_text(
        """
dataset:
  name: fixture
  schema_version: tmdb-keyed-v1
  raw_dir: raw
  enriched_metadata_path: raw/movies_enriched.parquet
  versions_dir: versions
prepare:
  compression: zstd
  compression_level: 3
  user_bucket_count: 2
split:
  train_fraction: 0.6
  validation_fraction: 0.2
  positive_rating_threshold: 4.0
  min_positive_interactions: 10
  min_train_interactions: 6
  seed_count: 5
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_raw(raw_dir: Path) -> None:
    raw_dir.mkdir()
    pd.DataFrame(
        {"movieId": [1, 2], "title": ["One", "Two"], "genres": ["Drama", "Comedy"]}
    ).to_csv(raw_dir / "movies.csv", index=False)
    pd.DataFrame({"movieId": [1, 2], "imdbId": [1, 2], "tmdbId": [101, 202]}).to_csv(
        raw_dir / "links.csv", index=False
    )
    pd.DataFrame(
        {
            "userId": [1, 1, 2],
            "movieId": [1, 2, 1],
            "rating": [5.0, 4.0, 3.0],
            "timestamp": [1, 2, 3],
        }
    ).to_csv(raw_dir / "ratings.csv", index=False)
    pd.DataFrame(
        {"userId": [1], "movieId": [1], "tag": ["good"], "timestamp": [1]}
    ).to_csv(raw_dir / "tags.csv", index=False)
    pd.DataFrame(
        {
            "movie_id": [1, 2],
            "tmdb_id": [101, 202],
            "title": ["One", "Two"],
            "genres": [["Drama"], ["Comedy"]],
        }
    ).to_parquet(raw_dir / "movies_enriched.parquet", index=False)


def test_prepare_writes_tmdb_catalog_and_resumable_interaction_parts(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    _write_raw(tmp_path / "raw")

    result = prepare_dataset(load_config(config_path), chunk_size=2)

    catalog = pd.read_parquet(result.version_dir / "catalog.parquet")
    parts = sorted((result.work_dir / "interaction_parts").glob("*.parquet"))
    assert catalog[["movielens_id", "tmdb_id", "item_index"]].to_dict("records") == [
        {"movielens_id": 1, "tmdb_id": 101, "item_index": 0},
        {"movielens_id": 2, "tmdb_id": 202, "item_index": 1},
    ]
    assert len(parts) == 2
    assert result.manifest["prepared_interaction_rows"] == 3

    resumed = prepare_dataset(load_config(config_path), chunk_size=2)
    assert resumed.version_dir == result.version_dir
    assert resumed.manifest["resumed_chunks"] == 2
