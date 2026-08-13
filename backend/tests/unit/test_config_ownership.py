from pathlib import Path


def test_canonical_config_family_and_legacy_boundary_are_explicit():
    configs = Path(__file__).parents[2] / "configs"
    for name in (
        "data_pipeline.yaml",
        "retrieval_training.yaml",
        "ranking_data.yaml",
        "ranking_features.yaml",
        "ranking_training.yaml",
        "evaluation.yaml",
        "mlflow.yaml",
        "settings.py",
    ):
        assert (configs / name).is_file()

    assert not (configs / "system.yml").exists()
    assert not (configs / "features.yml").exists()
    assert not (configs / "ranker.yml").exists()
