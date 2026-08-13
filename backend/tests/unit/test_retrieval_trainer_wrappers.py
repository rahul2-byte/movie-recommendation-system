from pathlib import Path


def test_retrieval_uses_only_canonical_trainer_entrypoints():
    retrieval_dir = Path(__file__).parents[2] / "training" / "retrieval"

    assert (retrieval_dir / "cli.py").is_file()
    assert (retrieval_dir / "build_als.py").is_file()
    assert (retrieval_dir / "build_two_tower.py").is_file()
    assert (retrieval_dir / "build_tfidf.py").is_file()
    assert (retrieval_dir / "build_item_graph.py").is_file()
    assert not (retrieval_dir / "train_als.py").exists()
    assert not (retrieval_dir / "train_two_tower.py").exists()
    assert not (retrieval_dir / "build_content.py").exists()
