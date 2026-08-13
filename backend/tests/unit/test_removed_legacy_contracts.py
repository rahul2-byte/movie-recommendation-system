from pathlib import Path


def test_legacy_schema_and_generated_summary_are_not_runtime_inputs():
    root = Path(__file__).parents[2]
    assert not (root / "api" / "schemas" / "movie.py").exists()
    assert (root / "api" / "schemas" / "recommend.py").is_file()
    assert not (root / "data" / "processed" / "movies_enriched.json").exists()
