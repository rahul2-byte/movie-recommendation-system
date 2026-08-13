from pathlib import Path


def test_obsolete_feature_generator_is_not_a_supported_entrypoint():
    features_dir = Path(__file__).parents[2] / "features"
    assert not (features_dir / "generate_training_features.py").exists()
