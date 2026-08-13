"""Typed request and response models for recommendation APIs."""

from typing import Annotated

from pydantic import BaseModel, Field

TMDBId = Annotated[int, Field(gt=0)]


class RecommendRequest(BaseModel):
    """Validate selected seed movies and the requested result count."""

    seed_tmdb_ids: list[TMDBId] = Field(
        min_length=1, max_length=5, description="User-selected seed movies"
    )

    moods: list[str] = Field(default_factory=list, description="Optional mood signals")

    limit: int = Field(
        default=99, ge=1, le=150, description="Number of recommendations"
    )


class MovieOut(BaseModel):
    """Movie metadata returned by the recommendation and catalog APIs."""

    tmdbId: int
    title: str
    year: int | None
    genres: list[str]
    posterUrl: str | None
    rating: float | None
    score: float | None = None


class RecommendResponse(BaseModel):
    """Represent the ranked movie records returned to the client."""

    recommendations: list[MovieOut]
