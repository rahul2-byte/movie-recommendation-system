import logging
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Add backend to path to allow imports
# We need to go up 2 levels from backend/features/native/run_sequences.py to get to backend/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

print(f"DEBUG: sys.path: {sys.path}")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

from common.config import config

# Paths
DIR = Path(__file__).parent.resolve()
BRIDGE_SCRIPT = DIR / "bridge.py"
SEQUENCE_BUILDER = DIR / "sequence_builder"
OUTPUT_PARQUET = Path(config.system.training_sequences_path)

CHUNK_SIZE = 500_000


def main():
    log.info("Running Sequence Generation Pipeline...")

    # We pipe python bridge -> sequence builder -> stdout -> python parser -> parquet
    # Note: bridge.py defaults to loading backend/data/processed/ratings.parquet

    cmd = f"python3 {BRIDGE_SCRIPT} | {SEQUENCE_BUILDER}"
    log.info(f"Executing: {cmd}")

    try:
        # Run command and capture stdout
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=sys.stderr
        )

        # Read the stdout as CSV into Pandas
        # sequence_builder outputs: query_movie_ids,candidate_movie_id,label
        csv_reader = pd.read_csv(process.stdout, chunksize=CHUNK_SIZE)

        first_chunk = True
        writer = None
        total_rows = 0

        for chunk in csv_reader:
            # query_movie_ids is string "id|id|id". Convert to list[int]
            chunk["query_movie_ids"] = chunk["query_movie_ids"].apply(
                lambda x: [int(i) for i in x.split("|")]
            )

            # Write to parquet
            table = pa.Table.from_pandas(chunk)

            if first_chunk:
                writer = pq.ParquetWriter(
                    OUTPUT_PARQUET, table.schema, compression="snappy"
                )
                first_chunk = False

            writer.write_table(table)
            total_rows += len(chunk)

            if total_rows % 5_000_000 == 0:
                log.info(f"Processed {total_rows} rows...")

        if writer:
            writer.close()

        process.wait()
        if process.returncode != 0:
            raise RuntimeError("Sequence builder failed.")

        log.info(
            f"Sequence generation complete. Saved {total_rows} rows to {OUTPUT_PARQUET}"
        )

    except Exception as e:
        log.error(f"Failed to run sequence pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
