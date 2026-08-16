"""Typed request and response models for recommendation APIs."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

TMDBId = Annotated[int, Field(gt=0)]
MoodName = Literal["DARK", "FEEL_GOOD", "INSPIRING", "FOCUS", "CHILL", "ADVENTURE"]


class RecommendRequest(BaseModel):
    """Validate selected seed movies and the requested result count."""

    seed_tmdb_ids: list[TMDBId] = Field(
        min_length=1, max_length=5, description="User-selected seed movies"
    )

    moods: list[MoodName] = Field(
        default_factory=list,
        description="Compatibility field; the current ranker does not use moods.",
    )

    limit: int = Field(
        default=200, ge=1, le=200, description="Number of recommendations"
    )

    refresh_seed: int | None = Field(default=None, ge=0)


class MovieOut(BaseModel):
    """Movie metadata returned by the recommendation and catalog APIs."""

    tmdbId: int
    title: str
    year: int | None
    genres: list[str]
    posterUrl: str | None
    rating: float | None
    rankScore: float | None = None


class RecommendResponse(BaseModel):
    """Represent the ranked movie records returned to the client."""

    recommendations: list[MovieOut]
    sessionId: str
    nextOffset: int | None
    hasMore: bool
