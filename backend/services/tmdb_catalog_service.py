import os
import requests
from typing import List, Dict
from fastapi import HTTPException

TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")

if not TMDB_TOKEN:
    raise RuntimeError("TMDB_ACCESS_TOKEN not set")

HEADERS = {
    "Authorization": f"Bearer {TMDB_TOKEN}",
    "Accept": "application/json",
}

TMDB_TIMEOUT = 8


def _tmdb_get(path: str, params: dict | None = None):
    try:
        response = requests.get(
            f"{TMDB_BASE_URL}{path}",
            headers=HEADERS,
            params=params or {},
            timeout=TMDB_TIMEOUT,
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="TMDB timeout")

    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"TMDB auth or request error: {e.response.text}",
        )

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))



def normalize_tmdb_movie(movie: Dict) -> Dict:
    return {
        "tmdbId": movie["id"],
        "title": movie["title"],
        "year": int(movie["release_date"][:4]) if movie.get("release_date") else None,
        "genres": [],  # optional: enrich later via genre map
        "rating": movie.get("vote_average"),
        "posterUrl": (
            f"{IMAGE_BASE_URL}{movie['poster_path']}"
            if movie.get("poster_path")
            else None
        ),
        "overview": movie.get("overview"),
    }


def fetch_trending_movies(limit: int = 20) -> List[Dict]:
    data = _tmdb_get("/trending/movie/week", {})
    return [normalize_tmdb_movie(m) for m in data["results"][:limit]]


def fetch_popular_movies(limit: int = 20) -> List[Dict]:
    data = _tmdb_get("/movie/popular", {})
    return [normalize_tmdb_movie(m) for m in data["results"][:limit]]


def fetch_new_releases(limit: int = 20) -> List[Dict]:
    data = _tmdb_get(
        "/discover/movie",
        {
            "sort_by": "release_date.desc",
            "primary_release_date.lte": "2025-12-31",
        },
    )
    return [normalize_tmdb_movie(m) for m in data["results"][:limit]]
