from typing import List
from pydantic import BaseModel, Field

from api.domain.moods import MOOD


class RecommendRequest(BaseModel):
    # Canonical input
    seed_movie_ids: List[int] = Field(
        min_length=1,
        max_length=5,
        description="User-selected seed movies"
    )

    moods: List[str] = Field(
        default_factory=list,
        description="Optional mood signals"
    )

    limit: int = Field(
        default=99,
        le=150,
        description="Number of recommendations"
    )


class MovieOut(BaseModel):
    movieId: int
    title: str
    year: int | None
    genres: List[str]
    tmdbId: int | None
    posterUrl: str | None
    rating: float | None
    score: float | None = None


class RecommendResponse(BaseModel):
    recommendations: List[MovieOut]
