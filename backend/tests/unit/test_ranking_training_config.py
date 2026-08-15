from pathlib import Path

import pytest
from training.ranking.config import RankingTrainingConfig, load_ranking_training_config


def test_load_ranking_training_config_reads_explicit_model_contract():
    config = load_ranking_training_config(
        Path("backend/configuration/ranking_training.yaml")
    )

    assert isinstance(config, RankingTrainingConfig)
    assert config.random_seed == 42
    assert config.ndcg_ks == (5, 10)
    assert config.early_stopping_rounds == 30
    assert config.packed_data_dir == Path("backend/artifacts/ranking_packed")


def test_load_ranking_training_config_rejects_non_positive_rounds(tmp_path):
    config_path = tmp_path / "ranking_training.yaml"
    config_path.write_text(
        "\n".join(
            [
                "random_seed: 42",
                "packing:",
                "  output_dir: backend/artifacts/ranking_packed",
                "model:",
                "  num_boost_round: 0",
                "  early_stopping_rounds: 30",
                "  ndcg_ks: [5, 10]",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="num_boost_round must be positive"):
        load_ranking_training_config(config_path)
