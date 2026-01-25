import pandas as pd
from typing import List
from api.recommend.types import Candidate
from api.recommend.movie_index import get_movie


def build_features(
    candidates: List[Candidate],
    seed_movie_ids: List[int],
) -> pd.DataFrame:

    rows = []

    seed_genres = set()
    for mid in seed_movie_ids:
        m = get_movie(mid)
        if m:
            seed_genres.update(m["genres"])

    for c in candidates:
        movie = get_movie(c.item_id)
        if not movie:
            continue

        row = {
            "item_id": c.item_id,
            "genre_overlap": len(
                seed_genres.intersection(movie["genres"])
            ),
        }

        # recall scores
        for source, score in c.scores.items():
            row[f"score_{source}"] = score

        # binary source flags
        for source in ["two_tower", "als", "item_cf", "content"]:
            row[f"from_{source}"] = int(source in c.sources)

        rows.append(row)

    df = pd.DataFrame(rows).fillna(0.0)
    return df
