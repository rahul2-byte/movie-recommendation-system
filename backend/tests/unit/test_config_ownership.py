from pathlib import Path


def test_orphaned_ranker_config_is_removed():
    configs = Path(__file__).parents[2] / "configs"
    assert not (configs / "ranker.yml").exists()
    assert (configs / "ranking_training.yaml").is_file()
    assert (configs / "ranking_features.yaml").is_file()
