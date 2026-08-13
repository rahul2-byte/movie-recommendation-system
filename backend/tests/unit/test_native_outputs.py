from pathlib import Path


def test_native_build_outputs_are_not_source_control_inputs():
    root = Path(__file__).parents[2]
    assert (root / "training" / "retrieval" / "native" / "Makefile").is_file()
    assert (root / "features" / "native" / "Makefile").is_file()
    assert not (root / "training" / "bin" / "train_als").exists()
    assert not (root / "training" / "retrieval" / "native" / "train_als").exists()
