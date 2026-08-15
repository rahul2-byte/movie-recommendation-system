from __future__ import annotations

from pathlib import Path

import pytest
from training.retrieval.cli import _resolve_content_lineage_path, _resolve_train_path


def test_retrieval_cli_uses_explicit_training_data_path(tmp_path: Path):
    explicit = tmp_path / "retrieval_train.parquet"
    explicit.touch()

    assert _resolve_train_path(tmp_path, explicit) == explicit.resolve()


def test_retrieval_cli_rejects_missing_explicit_training_data(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Retrieval training data not found"):
        _resolve_train_path(tmp_path, tmp_path / "missing.parquet")


def test_content_cli_uses_inner_interaction_history_for_artifact_lineage(
    tmp_path: Path,
):
    inner_history = tmp_path / "retrieval_train.parquet"
    inner_history.touch()

    assert (
        _resolve_content_lineage_path(tmp_path, inner_history)
        == inner_history.resolve()
    )
