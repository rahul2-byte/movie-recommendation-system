import asyncio

from infrastructure.metadata.movie_store import MovieStore


class FakeTMDBClient:
    def __init__(self):
        self.calls = []

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
            "videos": {
                "results": [
                    {
                        "site": "YouTube",
                        "type": "Trailer",
                        "official": True,
                        "key": "official-trailer",
                    }
                ]
            },
        }

    async def fetch_path(self, path: str, params=None):
        self.calls.append((path, params))
        assert path == "/search/movie"
        assert params["query"] == "example"
        return {
            "results": [
                {
                    "id": 603,
                    "title": "Example",
                    "release_date": "2024-01-02",
                    "genre_ids": [18],
                    "poster_path": "/poster.jpg",
                    "vote_average": 7.5,
                    "overview": "A complete search result.",
                }
            ]
        }


class PartiallyFailingTMDBClient(FakeTMDBClient):
    async def fetch_movie_full(self, tmdb_id: int):
        if tmdb_id == 680:
            raise RuntimeError("TMDB unavailable")
        return await super().fetch_movie_full(tmdb_id)


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
    assert movie["backdropUrl"] == ("https://image.tmdb.org/t/p/w1280/backdrop.jpg")
    assert movie["cast"] == ["Actor"]
    assert movie["trailerUrl"] == "https://www.youtube.com/watch?v=official-trailer"
    assert [entry["tmdbId"] for entry in movies] == [603, 680]
    assert search == [
        {
            "tmdbId": 603,
            "movieId": 603,
            "title": "Example",
            "year": 2024,
            "genres": ["Drama"],
            "posterUrl": "https://image.tmdb.org/t/p/w342/poster.jpg",
            "backdropUrl": None,
            "rating": 7.5,
            "overview": "A complete search result.",
        }
    ]
    assert not hasattr(store, "repository")


def test_movie_store_skips_failed_optional_metadata_in_batch():
    store = MovieStore(tmdb_client=PartiallyFailingTMDBClient())

    movies = asyncio.run(store.get_many([603, 680]))

    assert [movie["tmdbId"] for movie in movies] == [603]


def test_movie_store_search_forwards_the_requested_page():
    store = MovieStore(tmdb_client=FakeTMDBClient())

    asyncio.run(store.search("example", limit=20, page=3))

    assert store.tmdb_client.calls[-1] == (
        "/search/movie",
        {"query": "example", "page": "3"},
    )
