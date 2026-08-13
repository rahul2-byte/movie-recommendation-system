"""Configuration for reproducible offline evaluation runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class EvaluationConfig:
    """Validated settings for reproducible offline recommendation evaluation."""
    dataset_version: str
    output_dir: Path
    k_values: tuple[int, ...]
    ci_query_limit: int
    tfidf_seed_cache_batch_size: int
    fusion_candidate_k: int
    rrf_rank_constant: int
    mlflow_experiment_name: str


def load_evaluation_config(path: Path) -> EvaluationConfig:
    """Load and validate evaluation settings from one YAML file."""
    path = path.resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = payload.get("evaluation") if isinstance(payload, dict) else None
    if not isinstance(values, dict):
        raise ValueError("evaluation configuration must contain an evaluation mapping")
    dataset_version = values.get("dataset_version")
    output_dir = values.get("output_dir")
    k_values = values.get("k_values")
    ci_query_limit = values.get("ci_query_limit")
    seed_cache_batch_size = values.get("tfidf_seed_cache_batch_size")
    fusion_candidate_k = values.get("fusion_candidate_k")
    rrf_rank_constant = values.get("rrf_rank_constant")
    experiment = values.get("mlflow_experiment_name")
    if not isinstance(dataset_version, str) or not dataset_version:
        raise ValueError("evaluation.dataset_version must be a non-empty string")
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("evaluation.output_dir must be a non-empty path")
    if not isinstance(k_values, list) or not k_values:
        raise ValueError("evaluation.k_values must be a non-empty list")
    try:
        normalized_k = tuple(sorted(set(int(k) for k in k_values)))
    except (TypeError, ValueError) as error:
        raise ValueError("evaluation.k_values must contain integers") from error
    if normalized_k[0] < 1:
        raise ValueError("evaluation.k_values must contain positive integers")
    if not isinstance(ci_query_limit, int) or ci_query_limit < 1:
        raise ValueError("evaluation.ci_query_limit must be positive")
    if not isinstance(seed_cache_batch_size, int) or seed_cache_batch_size < 1:
        raise ValueError("evaluation.tfidf_seed_cache_batch_size must be positive")
    if not isinstance(fusion_candidate_k, int) or fusion_candidate_k < 1:
        raise ValueError("evaluation.fusion_candidate_k must be positive")
    if not isinstance(rrf_rank_constant, int) or rrf_rank_constant < 1:
        raise ValueError("evaluation.rrf_rank_constant must be positive")
    if not isinstance(experiment, str) or not experiment:
        raise ValueError("evaluation.mlflow_experiment_name must be a non-empty string")
    return EvaluationConfig(
        dataset_version=dataset_version,
        output_dir=(path.parent / output_dir).resolve(),
        k_values=normalized_k,
        ci_query_limit=ci_query_limit,
        tfidf_seed_cache_batch_size=seed_cache_batch_size,
        fusion_candidate_k=fusion_candidate_k,
        rrf_rank_constant=rrf_rank_constant,
        mlflow_experiment_name=experiment,
    )
