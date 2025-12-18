from pathlib import Path

import numpy as np

from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.registry import RetrieverRegistry

from orchestrator.retrievers.two_tower import TwoTowerRetriever
from orchestrator.retrievers.content import ContentBasedRetriever
from orchestrator.retrievers.als import ALSRetriever
from orchestrator.retrievers.item_cf import ItemCFRetriever


def main() -> None:
    user_id = 42
    recent_items = [1, 5, 9]

    # -------------------------------------------------
    # Load embeddings
    # -------------------------------------------------
    two_tower_user_emb = np.load("models/two_tower/user_embeddings.npy")

    als_user_emb = np.load("models/als/user_embeddings.npy")
    als_item_emb = np.load("models/als/item_embeddings.npy")

    # -------------------------------------------------
    # Instantiate retrievers
    # -------------------------------------------------
    retrievers = [
        TwoTowerRetriever(
            model_dir=Path("models/two_tower"),
            user_embeddings=two_tower_user_emb,
            index_path=Path("src/indices/two_tower")
        ),
        ALSRetriever(
            model_dir=Path("models/als"),
            user_embeddings=als_user_emb,
            index_path=Path("src/indices/als")
        ),
        ItemCFRetriever(
            model_dir=Path("models/als"),
            item_embeddings=als_item_emb,
            recent_item_ids=recent_items,
            index_path=Path("src/indices/als")
        ),
        ContentBasedRetriever(
            model_dir=Path("models/content_based"),
            index_path=Path("src/indices/content_based")
        ),
    ]

    quotas = {
        "two_tower": 80,
        "als": 60,
        "item_cf": 40,
        "content": 40,
    }

    registry = RetrieverRegistry(retrievers=retrievers, quotas=quotas)
    orchestrator = RecallOrchestrator(registry)

    # -------------------------------------------------
    # Run recall
    # -------------------------------------------------
    candidates = orchestrator.recall(
        user_id=user_id,
        seen_item_ids=recent_items,
    )

    print(f"\nReturned {len(candidates)} candidates\n")
    for c in candidates[:10]:
        print(c)


if __name__ == "__main__":
    main()
