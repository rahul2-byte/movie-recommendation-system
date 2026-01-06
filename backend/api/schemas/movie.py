from pydantic import BaseModel
from typing import List, Optional


class MovieOut(BaseModel):
    movieId: int
    title: str
    year: int
    genres: List[str]
    rating: Optional[float]
    posterUrl: Optional[str]
    overview: Optional[str]
