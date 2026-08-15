from pathlib import Path

from data_pipeline.storage.enrichment_checkpoint import CheckpointData


def test_legacy_schema_and_generated_summary_are_not_runtime_inputs():
    root = Path(__file__).parents[2]
    assert not (root / "api" / "schemas" / "movie.py").exists()
    assert (root / "api" / "schemas" / "recommend.py").is_file()
    assert not (root / "data" / "processed" / "movies_enriched.json").exists()


def test_checkpoint_instances_do_not_share_failed_movie_ids():
    first = CheckpointData()
    second = CheckpointData()

    first.failed_movie_ids.add(1)

    assert second.failed_movie_ids == set()
