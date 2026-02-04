"""
Data models for movie data structures.
"""
from dataclasses import dataclass, fields
from typing import List, Optional
import pyarrow as pa
import yaml
from pathlib import Path


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
        List[str]: pa.list_(pa.string()),
    }

    schema_fields = []
    for field in fields(MovieData):
        field_type = field.type
        # Handle Optional types (e.g., Optional[int] -> int)
        # In PyArrow, nullability is a property of the field, not the type.
        origin = getattr(field_type, "__origin__", None)
        is_optional = origin is Optional
        
        if is_optional:
            field_type = field_type.__args__[0]
            
        origin = getattr(field_type, "__origin__", None)
        if origin is list:
             # Assuming list of strings for genres, keywords, top_cast
            pa_type = pa.list_(pa.string())
        else:
            pa_type = type_mapping.get(field_type, pa.string())

        schema_fields.append(pa.field(field.name, pa_type, nullable=is_optional or field.name in ['overview', 'imdb_id', 'title']))
        
    return pa.schema(schema_fields)


def load_schema_version() -> dict:
    """
    Loads the current schema version details from the YAML file.

    Returns:
        A dictionary containing details of the current schema version.
    """
    # Path is relative to this file's location
    schema_config_path = Path(__file__).resolve().parent.parent.parent / "configs/schemas/schema_versions.yaml"
    with open(schema_config_path, 'r') as f:
        schema_config = yaml.safe_load(f)
    
    current_version_str = schema_config['current_version']
    return schema_config['versions'][current_version_str]


# Global schema variable
MOVIE_SCHEMA = get_pyarrow_schema()
