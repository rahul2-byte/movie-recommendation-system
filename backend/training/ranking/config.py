"""Explicit, versioned configuration for LambdaRank training."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RankingTrainingConfig:
    """Parameters that affect ranker training, selection, and packed inputs."""

    path: Path
    random_seed: int
    packed_data_dir: Path
    num_boost_round: int
    early_stopping_rounds: int
    ndcg_ks: tuple[int, ...]
    learning_rate: float
    num_leaves: int
    min_data_in_leaf: int
    lambda_l2: float
    num_threads: int
    rrf_rank_constant: int
    mlflow_experiment_name: str


def load_ranking_training_config(path: Path) -> RankingTrainingConfig:
    """Load the small ranker contract and reject unsafe training values."""
    path = path.resolve()
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("ranking training configuration must be a mapping")

    model = payload.get("model")
    packing = payload.get("packing")
    tracking = payload.get("tracking", {})
    if not isinstance(model, dict) or not isinstance(packing, dict):
        raise ValueError("model and packing configuration are required mappings")
    if not isinstance(tracking, dict):
        raise ValueError("tracking must be a mapping")
    ndcg_ks = model.get("ndcg_ks")
    if not isinstance(ndcg_ks, list) or not ndcg_ks:
        raise ValueError("model.ndcg_ks must be a non-empty list")

    config = RankingTrainingConfig(
        path=path,
        random_seed=int(payload.get("random_seed", 0)),
        packed_data_dir=Path(str(packing.get("output_dir", ""))),
        num_boost_round=int(model.get("num_boost_round", 0)),
        early_stopping_rounds=int(model.get("early_stopping_rounds", 0)),
        ndcg_ks=tuple(int(k) for k in ndcg_ks),
        learning_rate=float(model.get("learning_rate", 0)),
        num_leaves=int(model.get("num_leaves", 0)),
        min_data_in_leaf=int(model.get("min_data_in_leaf", 0)),
        lambda_l2=float(model.get("lambda_l2", -1)),
        num_threads=int(model.get("num_threads", 0)),
        rrf_rank_constant=int(model.get("rrf_rank_constant", 0)),
        mlflow_experiment_name=str(tracking.get("experiment_name", "")),
    )
    if not str(config.packed_data_dir):
        raise ValueError("packing.output_dir is required")
    if config.num_boost_round < 1:
        raise ValueError("num_boost_round must be positive")
    if config.early_stopping_rounds < 1:
        raise ValueError("early_stopping_rounds must be positive")
    if any(k < 1 for k in config.ndcg_ks):
        raise ValueError("model.ndcg_ks must contain positive values")
    if config.learning_rate <= 0:
        raise ValueError("model.learning_rate must be positive")
    if config.num_leaves < 2:
        raise ValueError("model.num_leaves must be at least two")
    if config.min_data_in_leaf < 1:
        raise ValueError("model.min_data_in_leaf must be positive")
    if config.lambda_l2 < 0:
        raise ValueError("model.lambda_l2 must be non-negative")
    if config.rrf_rank_constant < 1:
        raise ValueError("model.rrf_rank_constant must be positive")
    if not config.mlflow_experiment_name:
        raise ValueError("tracking.experiment_name is required")
    return config
