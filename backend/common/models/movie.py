"""
Data models for movie data structures.
"""

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Union, get_args, get_origin

import pyarrow as pa
import yaml


@dataclass
class MovieData:
    """Dataclass to hold enriched movie data."""

    movie_id: int
    tmdb_id: int | None
    imdb_id: str | None
    title: str | None
    overview: str | None
    genres: list[str]
    keywords: list[str]
    top_cast: list[str]
    director: str | None
    runtime_minutes: int | None
    release_year: int | None
    release_date: str | None
    popularity_score: float | None
    vote_count: int | None
    vote_average: float | None
    imdb_rating: float | None
    imdb_votes: int | None
    poster_path: str | None
    backdrop_path: str | None
    language: str | None
    country: str | None
    collection_id: int | None
    collection_name: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass to dictionary."""
        return asdict(self)


def get_pyarrow_schema() -> pa.Schema:
    """
    Generate PyArrow schema from the MovieData dataclass.

    Returns:
        PyArrow schema corresponding to MovieData fields
    """
    type_mapping = {
        int: pa.int64(),
        str: pa.string(),
        float: pa.float64(),
    }

    schema_fields = []
    for field in fields(MovieData):
        field_type = field.type
        origin = get_origin(field_type)
        args = get_args(field_type)

        is_optional = False

        # Handle Optional[T] which is Union[T, None]
        if origin is Union:
            if type(None) in args:
                is_optional = True
                # Get the underlying type
                underlying_types = [a for a in args if a is not type(None)]
                if underlying_types:
                    field_type = underlying_types[0]
                    origin = get_origin(field_type)
                    args = get_args(field_type)

        if origin is list or origin is list:
            pa_type = pa.list_(pa.string())
        else:
            pa_type = type_mapping.get(field_type, pa.string())

        schema_fields.append(pa.field(field.name, pa_type, nullable=is_optional))

    return pa.schema(schema_fields)


def load_schema_version() -> dict:
    """
    Loads the current schema version details from the YAML file.

    Returns:
        A dictionary containing details of the current schema version.
    """
    # Path is relative to this file's location
    schema_config_path = (
        Path(__file__).resolve().parent.parent.parent
        / "configs/schemas/schema_versions.yaml"
    )
    with open(schema_config_path) as f:
        schema_config = yaml.safe_load(f)

    current_version_str = schema_config["current_version"]
    return schema_config["versions"][current_version_str]


# Global schema variable
MOVIE_SCHEMA = get_pyarrow_schema()
