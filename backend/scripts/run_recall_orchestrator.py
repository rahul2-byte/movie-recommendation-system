"""
Offline Recall Evaluation (Deep Diagnostics)

Purpose:
- Validate retrieval quality end-to-end
- Understand retriever behavior, overlap, and bias
- Produce MLflow runs that explain *why* results look the way they do
"""

from pathlib import Path
from typing import List, Tuple
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
import mlflow

from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.registry import RetrieverRegistry
from orchestrator.retrievers.two_tower import TwoTowerRetriever
from orchestrator.retrievers.content import ContentBasedRetriever
from orchestrator.retrievers.meta_based import MetaBasedRetriever
from orchestrator.retrievers.item_cf import ItemCFRetriever


# -----------------------------
# Config
# -----------------------------
MIN_RATINGS_PER_USER = 20
HOLDOUT_FRACTION = 0.3
TOP_K_EVAL = 100
MAX_USERS = 500


# -----------------------------
# Utility functions
# -----------------------------
def split_user_history(
    item_ids: List[int],
) -> Tuple[List[int], List[int]]:
    split_idx = int(len(item_ids) * (1 - HOLDOUT_FRACTION))
    return item_ids[:split_idx], item_ids[split_idx:]


def recall_at_k(
    retrieved: List[int],
    relevant: List[int],
    k: int,
) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]).intersection(relevant)) / len(relevant)


# -----------------------------
# Main evaluation
# -----------------------------
def main() -> None:
    # -------------------------
    # Load ratings
    # -------------------------
    ratings = pd.read_parquet(
        "./backend/data/processed/ratings.parquet",
        columns=["userId", "movieId", "rating", "timestamp"],
    )

    ratings = ratings.sort_values("timestamp")

    user_groups = (
        ratings.groupby("userId")["movieId"]
        .apply(list)
        .reset_index()
    )

    user_groups = user_groups[
        user_groups["movieId"].apply(len) >= MIN_RATINGS_PER_USER
    ].head(MAX_USERS)

    rating_lookup = (
        ratings.groupby("movieId")["rating"]
        .agg(list)
        .to_dict()
    )

    # -------------------------
    # Load embeddings
    # -------------------------
    two_tower_user_emb = np.load(
        "./backend/models/two_tower/user_embeddings.npy"
    )
    als_item_emb = np.load(
        "./backend/models/als/item_embeddings.npy"
    )

    # -------------------------
    # Instantiate retrievers
    # -------------------------
    retrievers = [
        TwoTowerRetriever(
            model_dir=Path("./backend/models/two_tower"),
            user_embeddings=two_tower_user_emb,
            index_path=Path("./backend/indices/two_tower"),
        ),
        MetaBasedRetriever(
            model_dir=Path("./backend/models/meta_based"),
            index_path=Path("./backend/indices/meta_based"),
        ),
        ItemCFRetriever(
            model_dir=Path("./backend/models/als"),
            item_embeddings=als_item_emb,
            index_path=Path("./backend/indices/als"),
        ),
        ContentBasedRetriever(
            model_dir=Path("./backend/models/content_based"),
            index_path=Path("./backend/indices/content_based"),
        ),
    ]

    quotas = {
        "two_tower": 80,
        "item_cf": 60,
        "content": 60,
        "meta": 70,
    }

    registry = RetrieverRegistry(retrievers=retrievers, quotas=quotas)
    orchestrator = RecallOrchestrator(registry)

    # -------------------------
    # Global accumulators
    # -------------------------
    recall_scores = []

    retriever_item_counts = Counter()
    retriever_rating_values = defaultdict(list)
    overlap_counter = Counter()

    # -------------------------
    # MLflow run
    # -------------------------
    with mlflow.start_run(run_name="offline_recall_deep_eval"):
        mlflow.log_params({
            "min_ratings_per_user": MIN_RATINGS_PER_USER,
            "holdout_fraction": HOLDOUT_FRACTION,
            "top_k_eval": TOP_K_EVAL,
            "num_users": len(user_groups),
        })

        for _, row in user_groups.iterrows():
            user_id = int(row["userId"])
            items = row["movieId"]

            seen_items, held_out_items = split_user_history(items)
            if not held_out_items:
                continue

            candidates = orchestrator.recall(
                user_id=user_id,
                seen_item_ids=seen_items,
            )

            retrieved_ids = [c.item_id for c in candidates]

            # Recall
            recall_scores.append(
                recall_at_k(retrieved_ids, held_out_items, TOP_K_EVAL)
            )

            # -------------------------
            # Per-candidate diagnostics
            # -------------------------
            for c in candidates:
                retriever_count = len(c.sources)
                overlap_counter[retriever_count] += 1

                for src in c.sources:
                    retriever_item_counts[src] += 1

                    if c.item_id in rating_lookup:
                        retriever_rating_values[src].extend(
                            rating_lookup[c.item_id]
                        )

        # -------------------------
        # Aggregate recall metrics
        # -------------------------
        mlflow.log_metric("recall_at_k_mean", float(np.mean(recall_scores)))
        mlflow.log_metric("recall_at_k_median", float(np.median(recall_scores)))

        # -------------------------
        # Retriever contribution
        # -------------------------
        for retriever, count in retriever_item_counts.items():
            mlflow.log_metric(f"{retriever}_num_recommendations", count)

        # -------------------------
        # Overlap diagnostics
        # -------------------------
        total_candidates = sum(overlap_counter.values())
        for k in sorted(overlap_counter):
            mlflow.log_metric(
                f"items_from_{k}_retrievers_pct",
                overlap_counter[k] / total_candidates,
            )

        # -------------------------
        # Rating bias diagnostics
        # -------------------------
        for retriever, values in retriever_rating_values.items():
            if not values:
                continue

            mlflow.log_metric(
                f"{retriever}_rating_mean", float(np.mean(values))
            )
            mlflow.log_metric(
                f"{retriever}_rating_median", float(np.median(values))
            )

            mode_rating = Counter(values).most_common(1)[0][0]
            mlflow.log_metric(
                f"{retriever}_rating_mode", float(mode_rating)
            )

        print("\nOffline Recall Deep Evaluation Completed")
        print(f"Users evaluated: {len(recall_scores)}")
        print(f"Mean Recall@{TOP_K_EVAL}: {np.mean(recall_scores):.4f}")


if __name__ == "__main__":
    main()
