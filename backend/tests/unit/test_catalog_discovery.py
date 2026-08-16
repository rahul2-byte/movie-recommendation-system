import asyncio

import infrastructure.metadata.catalog_service as catalog


class _Client:
    def __init__(self):
        self.calls = []

    async def fetch_path(self, path, params=None):
        self.calls.append((path, params))
        if path == "/genre/movie/list":
            return {"genres": [{"id": 18, "name": "Drama"}]}
        return {
            "results": [
                {
                    "id": 603,
                    "title": "Example",
                    "release_date": "2024-01-02",
                    "genre_ids": [18],
                    "poster_path": "/poster.jpg",
                    "backdrop_path": "/backdrop.jpg",
                    "vote_average": 7.5,
                    "overview": "Example overview",
                }
            ]
        }


def test_discover_maps_filters_and_normalizes_movie(monkeypatch):
    client = _Client()
    monkeypatch.setattr(catalog, "get_tmdb_client", lambda: client)

    movies = asyncio.run(
        catalog.fetch_discover_movies(
            limit=12,
            genre_id=18,
            year_from=2020,
            year_to=2025,
            rating_min=7.0,
            sort="rating",
            page=2,
        )
    )

    assert client.calls == [
        (
            "/discover/movie",
            {
                "page": "2",
                "sort_by": "vote_average.desc",
                "vote_count.gte": "100",
                "with_genres": "18",
                "primary_release_date.gte": "2020-01-01",
                "primary_release_date.lte": "2025-12-31",
                "vote_average.gte": "7.0",
            },
        )
    ]
    assert movies[0]["genres"] == ["Drama"]
    assert movies[0]["backdropUrl"].endswith("/backdrop.jpg")


def test_genres_and_similar_titles_use_tmdb_contract(monkeypatch):
    client = _Client()
    monkeypatch.setattr(catalog, "get_tmdb_client", lambda: client)

    genres = asyncio.run(catalog.fetch_genres())
    similar = asyncio.run(catalog.fetch_similar_movies(603, 8))

    assert genres == [{"id": 18, "name": "Drama"}]
    assert client.calls[1] == ("/movie/603/similar", {"page": "1"})
    assert similar[0]["tmdbId"] == 603
