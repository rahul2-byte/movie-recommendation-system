from typing import List, Dict
from common.clients.tmdb import TMDBClient
from configs.settings import TMDB_IMAGE_BASE

IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Instantiate client
client = TMDBClient()

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


async def fetch_trending_movies(limit: int = 20) -> List[Dict]:
    await client.start()
    data = await client.fetch_path("/trending/movie/week")
    return [normalize_tmdb_movie(m) for m in data["results"][:limit]]


async def fetch_popular_movies(limit: int = 20) -> List[Dict]:
    await client.start()
    data = await client.fetch_path("/movie/popular")
    return [normalize_tmdb_movie(m) for m in data["results"][:limit]]


async def fetch_new_releases(limit: int = 20) -> List[Dict]:


    await client.start()


    data = await client.fetch_path(


        "/discover/movie",


        {


            "sort_by": "release_date.desc",


            "primary_release_date.lte": "2025-12-31",


        },


    )


    return [normalize_tmdb_movie(m) for m in data["results"][:limit]]

