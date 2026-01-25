"""
Field extraction service for transforming raw API data to MovieData.

Provides pure functions for normalizing and extracting fields from
TMDB and IMDb API responses.
"""

from typing import Dict, List, Optional

from utils.models.movie import MovieData
from utils.logger import get_logger

logger = get_logger(__name__)


def safe_int(value, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert value to int.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def extract_genres(movie_data: Dict) -> List[str]:
    """
    Extract genre names from TMDB movie data.
    
    Args:
        movie_data: TMDB movie response
        
    Returns:
        List of lowercase genre names
    """
    genres = movie_data.get("genres", [])
    return [
        g.get("name", "").lower()
        for g in genres
        if g.get("name")
    ]


def extract_keywords(movie_data: Dict) -> List[str]:
    """
    Extract keywords from TMDB movie data.
    
    TMDB API inconsistency: keywords can be under 'keywords' or 'results'.
    
    Args:
        movie_data: TMDB movie response with keywords appended
        
    Returns:
        List of lowercase keyword names
    """
    keywords_obj = movie_data.get("keywords", {})
    keyword_list = keywords_obj.get("keywords") or keywords_obj.get("results") or []
    
    return [
        k.get("name", "").lower()
        for k in keyword_list
        if k.get("name")
    ]


def extract_cast(movie_data: Dict, top_n: int = 5) -> List[str]:
    """
    Extract top cast members from TMDB credits.
    
    Args:
        movie_data: TMDB movie response with credits appended
        top_n: Number of top cast members to extract
        
    Returns:
        List of lowercase cast member names
    """
    credits = movie_data.get("credits", {})
    cast_list = credits.get("cast", [])
    
    return [
        c.get("name", "").lower()
        for c in cast_list[:top_n]
        if c.get("name")
    ]


def extract_director(movie_data: Dict) -> Optional[str]:
    """
    Extract director name from TMDB credits.
    
    Args:
        movie_data: TMDB movie response with credits appended
        
    Returns:
        Lowercase director name or None
    """
    credits = movie_data.get("credits", {})
    crew_list = credits.get("crew", [])
    
    for crew_member in crew_list:
        if crew_member.get("job") == "Director" and crew_member.get("name"):
            return crew_member.get("name", "").lower()
    
    return None


def extract_release_year(release_date: Optional[str]) -> Optional[int]:
    """
    Extract year from release date string.
    
    Args:
        release_date: Date string in YYYY-MM-DD format
        
    Returns:
        Year as integer or None
    """
    if not release_date or len(release_date) < 4:
        return None
    
    try:
        return int(release_date[:4])
    except ValueError:
        return None


def extract_imdb_rating(imdb_data: Dict) -> Optional[float]:
    """
    Extract IMDb rating from OMDb response.
    
    Args:
        imdb_data: OMDb API response
        
    Returns:
        Rating as float or None if invalid/missing
    """
    rating_str = imdb_data.get("imdbRating")
    if not rating_str or rating_str == "N/A":
        return None
    
    return safe_float(rating_str)


def extract_imdb_votes(imdb_data: Dict) -> Optional[int]:
    """
    Extract IMDb vote count from OMDb response.
    
    Vote counts contain commas (e.g., "1,234,567").
    
    Args:
        imdb_data: OMDb API response
        
    Returns:
        Vote count as integer or None if invalid/missing
    """
    votes_str = imdb_data.get("imdbVotes")
    if not votes_str or votes_str == "N/A":
        return None
    
    # Remove commas and convert
    try:
        return int(votes_str.replace(",", ""))
    except ValueError:
        return None


def extract_collection(movie_data: Dict) -> tuple[Optional[int], Optional[str]]:
    """
    Extract collection ID and name.
    
    Args:
        movie_data: TMDB movie response
        
    Returns:
        Tuple of (collection_id, collection_name)
    """
    collection = movie_data.get("belongs_to_collection") or {}
    return (
        collection.get("id"),
        collection.get("name"),
    )


def extract_movie_fields(
    movie_id: int,
    tmdb_data: Dict,
    imdb_data: Dict,
) -> MovieData:
    """
    Extract and normalize all fields from API responses.
    
    This is the main extraction function that transforms raw API data
    into a structured MovieData object.
    
    Args:
        movie_id: Original MovieLens movie ID
        tmdb_data: Raw TMDB API response (with keywords and credits)
        imdb_data: Raw OMDb API response
        
    Returns:
        MovieData object with all extracted fields
        
    Example:
        >>> tmdb_data = await tmdb_client.fetch_movie_full(550)
        >>> imdb_data = await imdb_client.fetch_rating('tt0137523')
        >>> movie = extract_movie_fields(1, tmdb_data, imdb_data)
    """
    release_date = tmdb_data.get("release_date")
    collection_id, collection_name = extract_collection(tmdb_data)
    
    return MovieData(
        movie_id=movie_id,
        tmdb_id=tmdb_data.get("id"),
        imdb_id=tmdb_data.get("imdb_id"),
        title=tmdb_data.get("title"),
        overview=tmdb_data.get("overview"),
        genres=extract_genres(tmdb_data),
        keywords=extract_keywords(tmdb_data),
        top_cast=extract_cast(tmdb_data),
        director=extract_director(tmdb_data),
        runtime_minutes=safe_int(tmdb_data.get("runtime")),
        release_year=extract_release_year(release_date),
        release_date=release_date,
        popularity_score=safe_float(tmdb_data.get("popularity")),
        vote_count=safe_int(tmdb_data.get("vote_count")),
        vote_average=safe_float(tmdb_data.get("vote_average")),
        imdb_rating=extract_imdb_rating(imdb_data),
        imdb_votes=extract_imdb_votes(imdb_data),
        poster_path=tmdb_data.get("poster_path"),
        backdrop_path=tmdb_data.get("backdrop_path"),
        language=imdb_data.get("Language"),
        country=imdb_data.get("Country"),
        collection_id=collection_id,
        collection_name=collection_name
    )