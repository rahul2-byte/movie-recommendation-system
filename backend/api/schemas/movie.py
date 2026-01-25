"""
Data models and schema definitions for movie enrichment.

This module provides PyArrow schema definitions and utility functions
for working with movie data structures, now based on Pydantic.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import pyarrow as pa
import yaml

from backend.configs.settings import SCHEMA_VERSIONS_FILE


class MovieData(BaseModel):
    """
    Data class representing enriched movie information, using Pydantic.
    """
    
    movie_id: int
    tmdb_id: int
    imdb_id: Optional[str] = None
    title: Optional[str] = None
    overview: Optional[str] = None
    genres: Optional[List[str]] = Field(default_factory=list)
    keywords: Optional[List[str]] = Field(default_factory=list)
    top_cast: Optional[List[str]] = Field(default_factory=list)
    director: Optional[str] = None
    runtime_minutes: Optional[int] = None
    release_year: Optional[int] = None
    release_date: Optional[str] = None
    popularity_score: Optional[float] = None
    vote_count: Optional[int] = None
    vote_average: Optional[float] = None
    imdb_rating: Optional[float] = None
    imdb_votes: Optional[int] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    collection_id: Optional[int] = None
    collection_name: Optional[str] = None


class MovieOut(BaseModel):
    """
    Schema for movie data as returned by the API.
    """
    movieId: int = Field(..., alias="movie_id")
    title: str
    year: int = Field(..., alias="release_year")
    genres: List[str]
    rating: Optional[float] = Field(None, alias="vote_average")
    posterUrl: Optional[str] = Field(None, alias="poster_path")
    overview: Optional[str]

    class Config:
        populate_by_name = True


def load_schema_version(version: Optional[str] = None) -> Dict:
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
        raise FileNotFoundError(
            f"Schema file not found: {SCHEMA_VERSIONS_FILE}"
        )
    
    with open(SCHEMA_VERSIONS_FILE, "r") as f:
        schema_config = yaml.safe_load(f)
    
    target_version = version or schema_config["current_version"]
    
    if target_version not in schema_config["versions"]:
        raise ValueError(
            f"Schema version {target_version} not found. "
            f"Available: {list(schema_config['versions'].keys())}"
        )
    
    return schema_config["versions"][target_version]


def get_pyarrow_schema(version: Optional[str] = None) -> pa.Schema:
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