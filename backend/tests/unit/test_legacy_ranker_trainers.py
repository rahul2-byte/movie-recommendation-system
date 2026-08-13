from pathlib import Path


def test_only_canonical_ranker_entrypoint_remains():
    ranking_dir = Path(__file__).parents[2] / "training" / "ranking"

    assert (ranking_dir / "cli.py").is_file()
    assert (ranking_dir / "pipeline.py").is_file()
    assert not (ranking_dir / "train_ranker.py").exists()
    assert not (ranking_dir / "train_ranker_v2.py").exists()
    assert not (ranking_dir / "train_from_csv.py").exists()
