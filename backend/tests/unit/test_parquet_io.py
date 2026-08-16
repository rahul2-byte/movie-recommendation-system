from pathlib import Path

import pandas as pd
from data_pipeline.parquet_io import write_parquet


def test_write_parquet_creates_compressed_file_without_temporary_artifact(
    tmp_path: Path,
):
    path = tmp_path / "nested" / "movies.parquet"
    frame = pd.DataFrame({"tmdb_id": [603], "title": ["The Matrix"]})

    write_parquet(frame, path, compression="zstd", compression_level=3)

    assert pd.read_parquet(path).equals(frame)
    assert not path.with_name(f".{path.name}.tmp").exists()
