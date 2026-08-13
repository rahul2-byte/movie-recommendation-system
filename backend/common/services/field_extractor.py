"""
Field extraction and normalization for movie metadata.

Transforms raw API responses from TMDB and IMDb into a unified
MovieData model.
"""

from data_pipeline.movie_models import MovieData

from common.logger import get_logger

logger = get_logger(__name__)


def extract_movie_fields(
    movie_id: int,
    tmdb_data: dict,
    imdb_data: dict | None = None,
) -> MovieData:
    """
    Extract and normalize fields from API responses.

    Args:
        movie_id: Original MovieLens ID
        tmdb_data: Raw JSON response from TMDB
        imdb_data: Raw JSON response from IMDb (OMDb)

    Returns:
        Populated MovieData object
    """
    # 1. Basic Metadata
    title = tmdb_data.get("title") or tmdb_data.get("original_title")
    imdb_id = tmdb_data.get("imdb_id")

    # 2. Extract Genres
    genres = [g["name"].lower() for g in tmdb_data.get("genres", []) if "name" in g]

    # 3. Extract Keywords
    keywords = []
    kw_data = tmdb_data.get("keywords", {})
    if isinstance(kw_data, dict):
        keywords = [
            k["name"].lower() for k in kw_data.get("keywords", []) if "name" in k
        ]

    # 4. Extract Credits (Cast and Director)
    credits = tmdb_data.get("credits", {})
    top_cast = []
    if "cast" in credits:
        top_cast = [c["name"].lower() for c in credits["cast"][:5] if "name" in c]

    director = None
    if "crew" in credits:
        for member in credits["crew"]:
            if member.get("job") == "Director":
                director = member.get("name", "").lower()
                break

    # 5. Extract Release Year
    release_date = tmdb_data.get("release_date")
    release_year = None
    if release_date and len(release_date) >= 4:
        try:
            release_year = int(release_date[:4])
        except ValueError:
            pass

    # 6. Extract Collection
    collection_id = None
    collection_name = None
    belongs_to_collection = tmdb_data.get("belongs_to_collection")
    if belongs_to_collection:
        collection_id = belongs_to_collection.get("id")
        collection_name = belongs_to_collection.get("name")

    # 7. Language and Country
    language = tmdb_data.get("original_language")
    country = None
    production_countries = tmdb_data.get("production_countries", [])
    if production_countries:
        country = production_countries[0].get("name")

    # 8. Ratings (Merge TMDB and IMDb)
    # IMDb data (from OMDb)
    imdb_rating = None
    imdb_votes = None

    if imdb_data:
        try:
            r = imdb_data.get("imdbRating", "N/A")
            if r != "N/A":
                imdb_rating = float(r)

            v = imdb_data.get("imdbVotes", "N/A").replace(",", "")
            if v != "N/A":
                imdb_votes = int(v)
        except (ValueError, TypeError):
            pass

    return MovieData(
        movie_id=movie_id,
        tmdb_id=tmdb_data.get("id"),
        imdb_id=imdb_id,
        title=title,
        overview=tmdb_data.get("overview"),
        genres=genres,
        keywords=keywords,
        top_cast=top_cast,
        director=director,
        runtime_minutes=tmdb_data.get("runtime"),
        release_year=release_year,
        release_date=release_date,
        popularity_score=tmdb_data.get("popularity"),
        vote_count=tmdb_data.get("vote_count"),
        vote_average=tmdb_data.get("vote_average"),
        imdb_rating=imdb_rating,
        imdb_votes=imdb_votes,
        poster_path=tmdb_data.get("poster_path"),
        backdrop_path=tmdb_data.get("backdrop_path"),
        language=language,
        country=country,
        collection_id=collection_id,
        collection_name=collection_name,
    )
