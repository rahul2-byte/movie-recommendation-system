"""
Data models and schema definitions for movie enrichment.

This module provides PyArrow schema definitions and utility functions
for working with movie data structures, now based on Pydantic.
"""

import pyarrow as pa
import yaml
from configs.settings import SCHEMA_VERSIONS_FILE
from pydantic import BaseModel, Field


class MovieData(BaseModel):
    """
    Data class representing enriched movie information, using Pydantic.
    """

    movie_id: int
    tmdb_id: int
    imdb_id: str | None = None
    title: str | None = None
    overview: str | None = None
    genres: list[str] | None = Field(default_factory=list)
    keywords: list[str] | None = Field(default_factory=list)
    top_cast: list[str] | None = Field(default_factory=list)
    director: str | None = None
    runtime_minutes: int | None = None
    release_year: int | None = None
    release_date: str | None = None
    popularity_score: float | None = None
    vote_count: int | None = None
    vote_average: float | None = None
    imdb_rating: float | None = None
    imdb_votes: int | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    language: str | None = None
    country: str | None = None
    collection_id: int | None = None
    collection_name: str | None = None


class MovieOut(BaseModel):
    """
    Schema for movie data as returned by the API.
    """

    movieId: int = Field(..., alias="movie_id")
    title: str
    year: int = Field(..., alias="release_year")
    genres: list[str]
    rating: float | None = Field(None, alias="vote_average")
    posterUrl: str | None = Field(None, alias="poster_path")
    overview: str | None

    class Config:
        populate_by_name = True


def load_schema_version(version: str | None = None) -> dict:
    """
    Load schema definition from YAML configuration.

    Args:
        version: Specific version to load, or None for current version

    Returns:
        Dictionary containing schema definition

    Raises:
        FileNotFoundError: If schema file doesn't exist
        ValueError: If requested version not found
    """
    if not SCHEMA_VERSIONS_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_VERSIONS_FILE}")

    with open(SCHEMA_VERSIONS_FILE) as f:
        schema_config = yaml.safe_load(f)

    target_version = version or schema_config["current_version"]

    if target_version not in schema_config["versions"]:
        raise ValueError(
            f"Schema version {target_version} not found. "
            f"Available: {list(schema_config['versions'].keys())}"
        )

    return schema_config["versions"][target_version]


def get_pyarrow_schema(version: str | None = None) -> pa.Schema:
    """
    Generate PyArrow schema from YAML configuration.

    Args:
        version: Specific version to load, or None for current version

    Returns:
        PyArrow Schema object
    """
    schema_def = load_schema_version(version)

    # Type mapping from YAML to PyArrow
    type_map = {
        "int64": pa.int64(),
        "float64": pa.float64(),
        "string": pa.string(),
        "list<string>": pa.list_(pa.string()),
        "list<int64>": pa.list_(pa.int64()),
    }

    fields = []
    for field_def in schema_def["fields"]:
        field_name = field_def["name"]
        field_type_str = field_def["type"]
        nullable = field_def.get("nullable", True)

        if field_type_str not in type_map:
            raise ValueError(
                f"Unknown type '{field_type_str}' for field '{field_name}'"
            )

        pa_type = type_map[field_type_str]
        fields.append(pa.field(field_name, pa_type, nullable=nullable))

    return pa.schema(fields)


# Global schema instance for use throughout the application
MOVIE_SCHEMA = get_pyarrow_schema()
