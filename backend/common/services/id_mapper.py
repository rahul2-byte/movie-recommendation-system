from pathlib import Path

import pandas as pd


class MovieIdMapper:
    def __init__(
        self,
        links_path: Path,
        movies_path: Path,
    ):
        self.links_df = pd.read_csv(links_path)
        self.movies_df = pd.read_csv(movies_path)

        # tmdbId → movieId
        self.tmdb_to_movie = (
            self.links_df.dropna(subset=["tmdbId"])
            .set_index("tmdbId")["movieId"]
            .to_dict()
        )

        # movieId → metadata
        self.movie_meta = self.movies_df.set_index("movieId")[
            ["title", "genres"]
        ].to_dict(orient="index")

    def tmdb_to_movielens(self, tmdb_ids: list[int]) -> list[int]:
        movie_ids = []
        for tmdb_id in tmdb_ids:
            movie_id = self.tmdb_to_movie.get(tmdb_id)
            if movie_id is not None:
                movie_ids.append(int(movie_id))
        return movie_ids

    def get_movie_meta(self, movie_id: int) -> dict | None:
        return self.movie_meta.get(movie_id)
