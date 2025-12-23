from typing import List
from pydantic import BaseModel, Field, conlist


class RecommendRequest(BaseModel):
    seed_movie_ids: conlist(int, min_length=0, max_length=5) = Field(
        default_factory=list,
        description="Movie IDs selected by the user"
    )
    preferred_genres: List[str] = Field(
        default_factory=list,
        description="Optional genre preferences"
    )
    top_k: int = Field(
        default=99,
        ge=10,
        le=99,
        description="Number of recommendations to return"
    )


class RecommendationItem(BaseModel):
    item_id: int
    score: float


class RecommendResponse(BaseModel):
    recommendations: List[RecommendationItem]
