import logging
import os
import subprocess
import sys
from pathlib import Path

# Add backend to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

from common.config import config

# Paths
DIR = Path(__file__).parent.resolve()
RANKER_GEN_BIN = DIR / "ranker_feature_gen"
INPUT_SEQ = Path(config.system.training_sequences_path)
OUTPUT_DATA = Path(config.system.training_dataset_path)
METADATA = Path(config.system.movies_metadata_path)


def main():
    log.info("Running Ranker Feature Generation...")

    if not INPUT_SEQ.exists():
        log.error(f"Input sequence file {INPUT_SEQ} missing.")
        return

    cmd = [str(RANKER_GEN_BIN), str(INPUT_SEQ), str(OUTPUT_DATA), str(METADATA)]
    log.info(f"Executing: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error("Ranker feature generation failed.")
        log.error(result.stderr)
    else:
        log.info(result.stdout)
        log.info(f"Successfully created {OUTPUT_DATA}")


if __name__ == "__main__":
    main()
