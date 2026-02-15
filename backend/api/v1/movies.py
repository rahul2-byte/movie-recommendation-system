from common.lifecycle import get_movie_store
from fastapi import APIRouter, Query, Request, HTTPException
from typing import List, Dict, Any, Optional
import logging
from configs.settings import TMDB_IMAGE_BASE, TMDB_POSTER_SIZE

log = logging.getLogger(__name__)

router = APIRouter(prefix="/movies", tags=["Movies"])

@router.get("/search")
async def movie_search(
    request: Request,
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=5, le=20),
) -> List[dict]:
    movie_store = get_movie_store()
    return await movie_store.search(q, limit)

@router.get("/{movie_id}")
async def get_movie_by_id(
    request: Request,
    movie_id: int
) -> Dict[str, Any]:
    """
    Get movie details by internal MovieLens ID.
    """
    movie_store = get_movie_store()
    movie = await movie_store.get(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.get("/tmdb/{tmdb_id}")
async def get_movie_by_tmdb_id(
    request: Request,
    tmdb_id: int
) -> Dict[str, Any]:
    """
    Get movie details by TMDB ID.
    Hybrid Resolver:
    1. Checks Local DB (MovieLens) for rich features.
    2. Fallback to Live TMDB API for new releases (if not found in DB).
    3. Fallback to IMDb (OMDb) for missing fields.
    """
    movie_store = get_movie_store()
    
    # 1. Try to find in Local DB
    local_movie = await movie_store.get_by_tmdb_id(tmdb_id)
    if local_movie:
        return local_movie
        
    # 2. Fetch Live from TMDB
    try:
        # Use the clients attached to MovieStore (or get new ones)
        # Note: In new lifecycle, store has clients initialized
        tmdb_data = await movie_store.tmdb_client.fetch_movie_full(tmdb_id)
        if not tmdb_data:
             raise HTTPException(status_code=404, detail="Movie not found on TMDB")

        poster_url = None
        if tmdb_data.get("poster_path"):
            poster_url = f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{tmdb_data['poster_path']}"
            
        backdrop_url = None
        if tmdb_data.get("backdrop_path"):
             backdrop_url = f"{TMDB_IMAGE_BASE}/original{tmdb_data['backdrop_path']}"

        overview = tmdb_data.get("overview")

        # 3. FALLBACK: Try IMDb if assets are missing
        if not poster_url or not overview or not backdrop_url:
            imdb_id = tmdb_data.get("imdb_id")
            if imdb_id:
                imdb_data = await movie_store.imdb_client.fetch_rating(imdb_id)
                if imdb_data:
                    if not poster_url and imdb_data.get("Poster") != "N/A":
                        poster_url = imdb_data.get("Poster")
                    if not overview and imdb_data.get("Plot") != "N/A":
                        overview = imdb_data.get("Plot")
                    if not backdrop_url and poster_url:
                        backdrop_url = poster_url # Fallback to blurred poster

        genres = [g["name"] for g in tmdb_data.get("genres", [])]
        credits = tmdb_data.get("credits", {})
        director = next((m.get("name") for m in credits.get("crew", []) if m.get("job") == "Director"), None)
        cast = [m.get("name") for m in credits.get("cast", [])[:5]]

        return {
            "movieId": 0, # Virtual ID for new releases
            "tmdbId": tmdb_id,
            "title": tmdb_data.get("title"),
            "year": int(tmdb_data["release_date"][:4]) if tmdb_data.get("release_date") else None,
            "genres": genres,
            "popularity": tmdb_data.get("vote_count", 0),
            "posterUrl": poster_url,
            "backdropUrl": backdrop_url,
            "overview": overview,
            "tagline": tmdb_data.get("tagline"),
            "releaseDate": tmdb_data.get("release_date"),
            "runtime": tmdb_data.get("runtime"),
            "voteAverage": tmdb_data.get("vote_average"),
            "voteCountTmdb": tmdb_data.get("vote_count"),
            "director": director,
            "cast": cast,
            "rating": tmdb_data.get("vote_average")
        }
    except Exception as e:
        log.error(f"Error fetching live movie data: {e}")
        raise HTTPException(status_code=404, detail=f"Movie not found: {str(e)}")
