import json
from pathlib import Path

import lightgbm as lgb

from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.registry import RetrieverRegistry
from reranking.reranker import Reranker
from api.inference import RecommenderInference


def load_inference_pipeline() -> RecommenderInference:
    # -------------------------------
    # Load Recall Orchestrator
    # -------------------------------
    registry = RetrieverRegistry.load_from_disk()
    orchestrator = RecallOrchestrator(registry)

    # -------------------------------
    # Load Ranker
    # -------------------------------
    ranker = lgb.Booster(
        model_file="models/ranker/lgbm_lambdarank.txt"
    )

    with open("models/ranker/feature_list.json", "r") as f:
        feature_columns = json.load(f)

    # -------------------------------
    # Load Re-ranker
    # -------------------------------
    reranker = Reranker()

    return RecommenderInference(
        orchestrator=orchestrator,
        ranker=ranker,
        reranker=reranker,
        feature_columns=feature_columns,
    )
