"""Build validated, TMDB-keyed Parquet datasets from MovieLens source files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from data_pipeline.parquet_io import write_parquet
from hashing import sha256

SCHEMA_VERSION = "tmdb-keyed-v1"
COMPRESSION = "zstd"
COMPRESSION_LEVEL = 3
REQUIRED_RAW_COLUMNS = {
    "movies.csv": ("movieId", "title", "genres"),
    "links.csv": ("movieId", "imdbId", "tmdbId"),
    "ratings.csv": ("userId", "movieId", "rating", "timestamp"),
    "tags.csv": ("userId", "movieId", "tag", "timestamp"),
}


class DatasetValidationError(ValueError):
    """Raised when a source dataset cannot satisfy the training contract."""


def _require_columns(
    frame: pd.DataFrame, columns: tuple[str, ...], source: Path
) -> None:
    """Reject a source frame that cannot satisfy its schema contract."""
    missing = set(columns) - set(frame.columns)
    if missing:
        raise DatasetValidationError(
            f"{source} is missing required columns: {sorted(missing)}"
        )


def _integer_column(
    frame: pd.DataFrame, column: str, source: Path, *, nullable: bool = False
) -> pd.Series:
    """Coerce one identifier column and reject malformed values."""
    values = pd.to_numeric(frame[column], errors="coerce")
    if not nullable and values.isna().any():
        raise DatasetValidationError(f"{source} has malformed values in {column}")
    non_null = values.dropna()
    if not non_null.empty and not (non_null % 1 == 0).all():
        raise DatasetValidationError(f"{source} has non-integer values in {column}")
    return values.astype("Int64")


def _read_raw(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Load and validate all required MovieLens CSV inputs."""
    frames: dict[str, pd.DataFrame] = {}
    for filename, columns in REQUIRED_RAW_COLUMNS.items():
        path = raw_dir / filename
        if not path.is_file():
            raise DatasetValidationError(f"Missing required raw dataset: {path}")
        frame = pd.read_csv(path)
        _require_columns(frame, columns, path)
        frames[filename] = frame

    for filename in ("movies.csv", "links.csv", "ratings.csv", "tags.csv"):
        frame = frames[filename]
        for column in ("movieId",):
            frame[column] = _integer_column(frame, column, raw_dir / filename)
    for filename in ("ratings.csv", "tags.csv"):
        frame = frames[filename]
        frame["userId"] = _integer_column(frame, "userId", raw_dir / filename)
        frame["timestamp"] = _integer_column(frame, "timestamp", raw_dir / filename)
    frames["links.csv"]["tmdbId"] = _integer_column(
        frames["links.csv"], "tmdbId", raw_dir / "links.csv", nullable=True
    )
    return frames


def _read_enriched(enriched_path: Path) -> pd.DataFrame:
    """Load and validate the enriched metadata parquet input."""
    if not enriched_path.is_file():
        raise DatasetValidationError(f"Missing enriched metadata: {enriched_path}")
    frame = pd.read_parquet(enriched_path)
    _require_columns(frame, ("movie_id", "tmdb_id"), enriched_path)
    frame = frame.copy()
    frame["movie_id"] = _integer_column(frame, "movie_id", enriched_path)
    frame["tmdb_id"] = _integer_column(frame, "tmdb_id", enriched_path, nullable=True)
    return frame


def _canonical_catalog(
    links: pd.DataFrame, enriched: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build the unique MovieLens/TMDB catalog and exclusion counts."""
    mappings = links[["movieId", "tmdbId"]].rename(
        columns={"movieId": "movielens_id", "tmdbId": "tmdb_id"}
    )
    summary = {
        "excluded_unmapped_rows": int(mappings["tmdb_id"].isna().sum()),
        "excluded_ambiguous_tmdb_rows": 0,
        "excluded_duplicate_movielens_rows": 0,
        "excluded_metadata_mismatch_rows": 0,
    }
    mappings = mappings.dropna(subset=["tmdb_id"]).copy()
    mappings["movielens_id"] = mappings["movielens_id"].astype("int64")
    mappings["tmdb_id"] = mappings["tmdb_id"].astype("int64")

    duplicate_tmdb = mappings["tmdb_id"].duplicated(keep=False)
    summary["excluded_ambiguous_tmdb_rows"] = int(duplicate_tmdb.sum())
    duplicate_movielens = mappings["movielens_id"].duplicated(keep=False)
    summary["excluded_duplicate_movielens_rows"] = int(duplicate_movielens.sum())
    mappings = mappings.loc[~duplicate_tmdb & ~duplicate_movielens]

    metadata = enriched.rename(columns={"movie_id": "movielens_id"}).copy()
    metadata = metadata.dropna(subset=["tmdb_id"])
    metadata["movielens_id"] = metadata["movielens_id"].astype("int64")
    metadata["tmdb_id"] = metadata["tmdb_id"].astype("int64")
    metadata = metadata.drop_duplicates(subset=["movielens_id", "tmdb_id"], keep=False)

    catalog = mappings.merge(
        metadata,
        on=["movielens_id", "tmdb_id"],
        how="inner",
        validate="one_to_one",
    )
    summary["excluded_metadata_mismatch_rows"] = int(len(mappings) - len(catalog))
    catalog = catalog.sort_values("tmdb_id", kind="stable").reset_index(drop=True)
    catalog.insert(2, "item_index", range(len(catalog)))
    return catalog, summary


def _canonical_interactions(
    source: pd.DataFrame, catalog: pd.DataFrame, *, has_tag: bool
) -> pd.DataFrame:
    """Map source events to valid TMDB IDs while preserving event fields."""
    columns = ["movielens_id", "tmdb_id"]
    mapping = catalog[columns]
    frame = source.rename(columns={"userId": "user_id", "movieId": "movielens_id"})
    frame = frame.merge(mapping, on="movielens_id", how="inner", validate="many_to_one")
    output_columns = ["user_id", "tmdb_id", "movielens_id"]
    if has_tag:
        output_columns.append("tag")
    else:
        output_columns.append("rating")
    output_columns.append("timestamp")
    return frame[output_columns]


def build_processed_dataset(
    raw_dir: Path, output_dir: Path, enriched_path: Path
) -> dict[str, int]:
    """Validate source data and write canonical Zstandard Parquet datasets."""
    raw_dir = raw_dir.resolve()
    output_dir = output_dir.resolve()
    enriched_path = enriched_path.resolve()
    raw = _read_raw(raw_dir)
    enriched = _read_enriched(enriched_path)
    catalog, summary = _canonical_catalog(raw["links.csv"], enriched)
    if catalog.empty:
        raise DatasetValidationError("No one-to-one MovieLens/TMDB catalog rows remain")

    ratings = _canonical_interactions(raw["ratings.csv"], catalog, has_tag=False)
    tags = _canonical_interactions(raw["tags.csv"], catalog, has_tag=True)
    for frame, name in (
        (raw["movies.csv"], "movies.parquet"),
        (raw["links.csv"], "links.parquet"),
        (catalog, "catalog.parquet"),
        (catalog, "movies_enriched.parquet"),
        (ratings, "ratings.parquet"),
        (tags, "tags.parquet"),
    ):
        write_parquet(
            frame,
            output_dir / name,
            compression=COMPRESSION,
            compression_level=COMPRESSION_LEVEL,
        )

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "compression": {"codec": COMPRESSION, "level": COMPRESSION_LEVEL},
        "identity": {
            "operational_id": "tmdb_id",
            "lineage_id": "movielens_id",
            "internal_index": "item_index",
        },
        "source_sha256": {
            filename: sha256(raw_dir / filename) for filename in REQUIRED_RAW_COLUMNS
        }
        | {"movies_enriched.parquet": sha256(enriched_path)},
        "catalog_rows": len(catalog),
        "ratings_rows": len(ratings),
        "tags_rows": len(tags),
        **summary,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        key: int(value) for key, value in manifest.items() if isinstance(value, int)
    }


def main() -> None:
    """Convert validated raw and enriched inputs into processed parquet files."""
    backend_dir = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=backend_dir / "data/raw")
    parser.add_argument(
        "--output-dir", type=Path, default=backend_dir / "data/processed"
    )
    parser.add_argument(
        "--enriched-path",
        type=Path,
        default=backend_dir / "data/raw/movies_enriched.parquet",
    )
    args = parser.parse_args()
    print(json.dumps(build_processed_dataset(**vars(args)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
