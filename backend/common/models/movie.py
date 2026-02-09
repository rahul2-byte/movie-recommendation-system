"""
Data models for movie data structures.
"""

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, get_args, get_origin

import pyarrow as pa
import yaml


@dataclass
class MovieData:
    """Dataclass to hold enriched movie data."""

    movie_id: int
    tmdb_id: Optional[int]
    imdb_id: Optional[str]
    title: Optional[str]
    overview: Optional[str]
    genres: List[str]
    keywords: List[str]
    top_cast: List[str]
    director: Optional[str]
    runtime_minutes: Optional[int]
    release_year: Optional[int]
    release_date: Optional[str]
    popularity_score: Optional[float]
    vote_count: Optional[int]
    vote_average: Optional[float]
    imdb_rating: Optional[float]
    imdb_votes: Optional[int]
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    language: Optional[str]
    country: Optional[str]
    collection_id: Optional[int]
    collection_name: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
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

        if origin is list or origin is List:
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
    with open(schema_config_path, "r") as f:
        schema_config = yaml.safe_load(f)

    current_version_str = schema_config["current_version"]
    return schema_config["versions"][current_version_str]


# Global schema variable
MOVIE_SCHEMA = get_pyarrow_schema()
