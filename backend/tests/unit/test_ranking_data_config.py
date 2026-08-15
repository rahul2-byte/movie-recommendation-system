from __future__ import annotations

from pathlib import Path

import pytest
from data_pipeline.config import ConfigError, load_ranking_data_config


def _write_config(
    path: Path,
    *,
    inner_train_fraction: float = 0.8,
    seed_count: int = 5,
) -> None:
    path.write_text(
        f"""
dataset_version: movielens-32m-example
inner_train_fraction: {inner_train_fraction}
positive_rating_threshold: 3.0
seed_count: {seed_count}
candidate_k: 200
retrievers: [als, item_graph, two_tower]
compression: zstd
compression_level: 3
random_seed: 42
tracking:
  experiment_name: ranking_data
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_load_ranking_data_config_parses_authoritative_contract(tmp_path: Path):
    path = tmp_path / "ranking_data.yaml"
    _write_config(path)

    config = load_ranking_data_config(path)

    assert config.dataset_version == "movielens-32m-example"
    assert config.seed_count == 5
    assert config.retrievers == ("als", "item_graph", "two_tower")
    assert config.minimum_events_per_user == 6


def test_load_ranking_data_config_accepts_content_retriever(tmp_path: Path):
    path = tmp_path / "ranking_data.yaml"
    _write_config(path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "retrievers: [als, item_graph, two_tower]",
            "retrievers: [als, item_graph, two_tower, content]",
        ),
        encoding="utf-8",
    )

    config = load_ranking_data_config(path)

    assert config.retrievers == ("als", "item_graph", "two_tower", "content")


@pytest.mark.parametrize(
    ("inner_train_fraction", "seed_count", "message"),
    [
        (1.0, 5, "inner_train_fraction"),
        (0.8, 0, "seed_count"),
    ],
)
def test_load_ranking_data_config_rejects_invalid_contract(
    tmp_path: Path,
    inner_train_fraction: float,
    seed_count: int,
    message: str,
):
    path = tmp_path / "ranking_data.yaml"
    _write_config(
        path,
        inner_train_fraction=inner_train_fraction,
        seed_count=seed_count,
    )

    with pytest.raises(ConfigError, match=message):
        load_ranking_data_config(path)
