"""Regression tests for canonical offline CLI configuration locations."""

from pathlib import Path

import pytest
from data_pipeline.cli import _default_config as data_pipeline_default_config
from evaluation.cli import _default_config as evaluation_default_config
from training.ranking.cli import _default_config as ranking_default_config
from training.retrieval.cli import _default_config as retrieval_default_config


@pytest.mark.parametrize(
    ("default_config", "filename"),
    [
        (data_pipeline_default_config, "data_pipeline.yaml"),
        (data_pipeline_default_config, "mlflow.yaml"),
        (evaluation_default_config, "evaluation.yaml"),
        (ranking_default_config, "ranking_training.yaml"),
        (retrieval_default_config, "retrieval_training.yaml"),
    ],
)
def test_cli_default_config_uses_the_canonical_configuration_directory(
    default_config, filename: str
) -> None:
    """Every supported CLI default must resolve to a checked-in YAML file."""
    path = default_config(filename)

    assert path.name == filename
    assert path.parent == Path(__file__).parents[2] / "configuration"
    assert path.is_file()
