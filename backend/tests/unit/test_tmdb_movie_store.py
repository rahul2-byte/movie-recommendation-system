import asyncio

from common.services.movie_store import MovieStore


class FakeTMDBClient:
    async def fetch_movie_full(self, tmdb_id: int):
        return {
            "id": tmdb_id,
            "title": "Example",
            "release_date": "2024-01-02",
            "genres": [{"name": "Drama"}],
            "keywords": {"keywords": [{"name": "memory"}]},
            "credits": {
                "crew": [{"job": "Director", "name": "Director"}],
                "cast": [{"name": "Actor"}],
            },
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
            "vote_average": 7.5,
            "vote_count": 100,
            "popularity": 8.5,
            "runtime": 120,
        }

    async def fetch_path(self, path: str, params=None):
        assert path == "/search/movie"
        assert params == {"query": "example"}
        return {"results": [{"id": 603, "title": "Example"}]}


def test_movie_store_uses_tmdb_for_metadata_and_search():
    store = MovieStore(tmdb_client=FakeTMDBClient())

    movie = asyncio.run(store.get(603))
    movies = asyncio.run(store.get_many([603, 680]))
    search = asyncio.run(store.search("example"))

    assert movie["tmdbId"] == 603
    assert movie["movieId"] == 603
    assert movie["genres"] == ["Drama"]
    assert movie["keywords"] == ["memory"]
    assert movie["posterUrl"].endswith("/poster.jpg")
    assert [entry["tmdbId"] for entry in movies] == [603, 680]
    assert search == [{"tmdbId": 603, "movieId": 603, "title": "Example"}]
    assert not hasattr(store, "repository")
