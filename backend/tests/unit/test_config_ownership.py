from pathlib import Path


def test_canonical_config_family_and_legacy_boundary_are_explicit():
    configuration = Path(__file__).parents[2] / "configuration"
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
        assert (configuration / name).is_file()

    assert not (configuration / "system.yml").exists()
    assert not (configuration / "features.yml").exists()
    assert not (configuration / "ranker.yml").exists()
