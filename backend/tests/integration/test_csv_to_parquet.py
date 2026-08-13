import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest
from scripts.data_enrichment.csv_to_parquet import (
    DatasetValidationError,
    build_processed_dataset,
)


def _write_raw_dataset(raw_dir: Path) -> None:
    raw_dir.mkdir()
    pd.DataFrame(
        {
            "movieId": [1, 2, 3, 4, 5],
            "title": ["One", "Two", "Three", "Four", "Five"],
            "genres": ["Drama"] * 5,
        }
    ).to_csv(raw_dir / "movies.csv", index=False)
    pd.DataFrame(
        {
            "movieId": [1, 2, 3, 4, 5],
            "imdbId": [11, 22, 33, 44, 55],
            "tmdbId": [101, 202, 202, None, 505],
        }
    ).to_csv(raw_dir / "links.csv", index=False)
    pd.DataFrame(
        {
            "userId": [7, 7, 7, 7, 7],
            "movieId": [1, 2, 3, 4, 5],
            "rating": [5.0, 4.0, 3.0, 2.0, 1.0],
            "timestamp": [1, 2, 3, 4, 5],
        }
    ).to_csv(raw_dir / "ratings.csv", index=False)
    pd.DataFrame(
        {
            "userId": [7, 7],
            "movieId": [1, 2],
            "tag": ["good", "bad"],
            "timestamp": [1, 2],
        }
    ).to_csv(raw_dir / "tags.csv", index=False)


def _write_enriched(path: Path) -> None:
    pd.DataFrame(
        {
            "movie_id": [1, 2, 3, 5],
            "tmdb_id": [101, 202, 202, 999],
            "title": ["One", "Two", "Three", "Five"],
            "genres": [["Drama"]] * 4,
        }
    ).to_parquet(path, index=False)


def test_build_processed_dataset_uses_tmdb_as_the_operational_id(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    enriched_path = tmp_path / "movies_enriched.parquet"
    _write_raw_dataset(raw_dir)
    _write_enriched(enriched_path)

    summary = build_processed_dataset(raw_dir, output_dir, enriched_path)

    catalog = pd.read_parquet(output_dir / "catalog.parquet")
    ratings = pd.read_parquet(output_dir / "ratings.parquet")
    tags = pd.read_parquet(output_dir / "tags.parquet")
    assert catalog[["tmdb_id", "movielens_id", "item_index"]].to_dict("records") == [
        {"tmdb_id": 101, "movielens_id": 1, "item_index": 0}
    ]
    assert ratings.to_dict("records") == [
        {
            "user_id": 7,
            "tmdb_id": 101,
            "movielens_id": 1,
            "rating": 5.0,
            "timestamp": 1,
        }
    ]
    assert tags.to_dict("records") == [
        {
            "user_id": 7,
            "tmdb_id": 101,
            "movielens_id": 1,
            "tag": "good",
            "timestamp": 1,
        }
    ]
    assert summary["excluded_ambiguous_tmdb_rows"] == 2
    assert summary["excluded_unmapped_rows"] == 1
    assert summary["excluded_metadata_mismatch_rows"] == 1

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["schema_version"] == "tmdb-keyed-v1"
    assert manifest["catalog_rows"] == 1
    assert (
        pq.ParquetFile(output_dir / "ratings.parquet")
        .metadata.row_group(0)
        .column(0)
        .compression
        == "ZSTD"
    )


def test_build_processed_dataset_rejects_missing_required_source(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    enriched_path = tmp_path / "movies_enriched.parquet"
    _write_enriched(enriched_path)

    with pytest.raises(DatasetValidationError, match="Missing required raw dataset"):
        build_processed_dataset(raw_dir, tmp_path / "processed", enriched_path)
