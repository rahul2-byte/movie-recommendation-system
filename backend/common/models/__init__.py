"""Models package for movie data structures."""

from common.models.movie import MOVIE_SCHEMA, MovieData, get_pyarrow_schema

__all__ = [
    "MovieData",
    "MOVIE_SCHEMA",
    "get_pyarrow_schema",
]
