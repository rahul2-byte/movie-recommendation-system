from pathlib import Path
from api.services.id_mapper import MovieIdMapper

from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.registry import RetrieverRegistry

from orchestrator.retrievers.two_tower import TwoTowerRetriever
from orchestrator.retrievers.als import ALSRetriever
from orchestrator.retrievers.item_cf import ItemCFRetriever
from orchestrator.retrievers.content import ContentBasedRetriever

import numpy as np


class RecallService:
    def __init__(self) -> None:

        self.id_mapper = MovieIdMapper(
            links_path=Path("./backend/data/raw/links.csv"),
            movies_path=Path("./backend/data/raw/movies.csv"),
        )

        # -------------------------------
        # Load embeddings ONCE
        # -------------------------------
        self.two_tower_user_emb = np.load("./backend/models/two_tower/user_embeddings.npy")
        self.als_user_emb = np.load("./backend/models/als/user_embeddings.npy")
        self.als_item_emb = np.load("./backend/models/als/item_embeddings.npy")

        # -------------------------------
        # Instantiate retrievers
        # -------------------------------
        retrievers = [
            TwoTowerRetriever(
                model_dir=Path("./backend/models/two_tower"),
                user_embeddings=self.two_tower_user_emb,
                index_path=Path("./backend/indices/two_tower"),
            ),
            ALSRetriever(
                model_dir=Path("./backend/models/als"),
                user_embeddings=self.als_user_emb,
                index_path=Path("./backend/indices/als"),
            ),
            ItemCFRetriever(
                model_dir=Path("./backend/models/als"),
                item_embeddings=self.als_item_emb,
                index_path=Path("./backend/indices/als"),
            ),
            ContentBasedRetriever(
                model_dir=Path("./backend/models/content_based"),
                index_path=Path("./backend/indices/content_based"),
            ),
        ]

        quotas = {
            "two_tower": 800,
            "als": 700,
            "item_cf": 500,
            "content": 500,
        }

        registry = RetrieverRegistry(retrievers=retrievers, quotas=quotas)
        self.orchestrator = RecallOrchestrator(registry)

    def recall(self, seed_tmdb_ids: list[int], k: int = 2500):
        seed_movie_ids = self.id_mapper.tmdb_to_movielens(seed_tmdb_ids)

        if not seed_movie_ids:
            return []

        return self.orchestrator.recall(
            user_id=None,
            seen_item_ids=seed_movie_ids
        )
