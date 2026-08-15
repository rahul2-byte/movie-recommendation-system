"""Import contracts for the backend's discoverable module names."""

from importlib import import_module

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "configuration.settings",
        "observability.logging",
        "infrastructure.clients.tmdb",
        "serving.recommendation_pipeline",
        "serving.bundle_recommender",
        "evaluation.offline_evaluator",
        "evaluation.rank_fusion",
        "data_pipeline.ranking_dataset",
        "training.ranking.ranker_training",
        "training.retrieval.als_trainer",
        "training.retrieval.content_retriever",
        "training.retrieval.item_graph_trainer",
        "training.retrieval.two_tower_trainer",
    ],
)
def test_canonical_modules_are_importable(module_name: str):
    assert import_module(module_name)
