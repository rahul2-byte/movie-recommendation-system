from pathlib import Path


def test_retrieval_uses_only_canonical_trainer_entrypoints():
    retrieval_dir = Path(__file__).parents[2] / "training" / "retrieval"

    assert (retrieval_dir / "cli.py").is_file()
    assert (retrieval_dir / "als_trainer.py").is_file()
    assert (retrieval_dir / "two_tower_trainer.py").is_file()
    assert (retrieval_dir / "content_retriever.py").is_file()
    assert (retrieval_dir / "item_graph_trainer.py").is_file()
    assert not (retrieval_dir / "train_als.py").exists()
    assert not (retrieval_dir / "train_two_tower.py").exists()
    assert not (retrieval_dir / "build_content.py").exists()
    assert not (retrieval_dir / "build_tfidf.py").exists()
