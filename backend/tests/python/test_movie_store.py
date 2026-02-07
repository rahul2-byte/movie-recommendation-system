import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_movie_store_get(movie_store):
    """Test retrieving a single movie by ID."""
    movie = await movie_store.get(1)
    assert movie is not None
    assert movie["movieId"] == 1
    assert movie["title"] == "Toy Story (1995)"
    assert "Animation" in movie["genres"]
    assert movie["year"] == 1995

@pytest.mark.asyncio
async def test_movie_store_get_not_found(movie_store):
    """Test retrieving a non-existent movie."""
    movie = await movie_store.get(999999)
    assert movie is None

@pytest.mark.asyncio
async def test_movie_store_search(movie_store):
    """Test searching for movies by title."""
    results = await movie_store.search("Toy")
    assert len(results) >= 1
    assert results[0]["title"] == "Toy Story (1995)"

@pytest.mark.asyncio
async def test_movie_store_tmdb_integration(movie_store):
    """Test that TMDB fetch is attempted if tmdbId is present."""
    # Mock the internal TMDB fetcher
    movie_store._fetch_tmdb_movie = AsyncMock(return_value={
        "poster_path": "/test.jpg",
        "overview": "A test movie overview"
    })
    
    movie = await movie_store.get(1)
    assert movie["posterUrl"] is not None
    assert "test.jpg" in movie["posterUrl"]
    assert movie["overview"] == "A test movie overview"
    movie_store._fetch_tmdb_movie.assert_called_once_with(862)
