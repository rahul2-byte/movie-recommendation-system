import pandas as pd
from functools import lru_cache


@lru_cache(maxsize=1)
def load_movielens():
    movies = pd.read_csv("data/movies.csv")
    ratings = pd.read_csv("data/ratings.csv")

    movies["genres"] = movies["genres"].str.split("|")
    return movies, ratings
