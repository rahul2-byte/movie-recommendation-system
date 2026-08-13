from pathlib import Path

from evaluation.config import load_evaluation_config


def test_evaluation_config_resolves_paths_and_validates_k_values(tmp_path: Path):
    path = tmp_path / "evaluation.yaml"
    path.write_text(
        """
evaluation:
  dataset_version: fixture-123
  output_dir: artifacts/evaluation
  k_values: [10, 20]
  ci_query_limit: 25
  tfidf_seed_cache_batch_size: 512
  fusion_candidate_k: 200
  rrf_rank_constant: 60
  mlflow_experiment_name: offline_evaluation
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_evaluation_config(path)

    assert config.dataset_version == "fixture-123"
    assert config.output_dir == tmp_path / "artifacts/evaluation"
    assert config.k_values == (10, 20)
    assert config.tfidf_seed_cache_batch_size == 512
    assert config.fusion_candidate_k == 200
