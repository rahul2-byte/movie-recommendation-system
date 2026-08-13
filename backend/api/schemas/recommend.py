from typing import Annotated

from pydantic import BaseModel, Field

TMDBId = Annotated[int, Field(gt=0)]


class RecommendRequest(BaseModel):
    # Canonical input
    seed_tmdb_ids: list[TMDBId] = Field(
        min_length=1, max_length=5, description="User-selected seed movies"
    )

    moods: list[str] = Field(default_factory=list, description="Optional mood signals")

    limit: int = Field(
        default=99, ge=1, le=150, description="Number of recommendations"
    )


class MovieOut(BaseModel):
    tmdbId: int
    title: str
    year: int | None
    genres: list[str]
    tmdbId: int | None
    posterUrl: str | None
    rating: float | None
    score: float | None = None


class RecommendResponse(BaseModel):
    recommendations: list[MovieOut]
