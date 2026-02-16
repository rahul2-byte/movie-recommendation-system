import subprocess
import logging
import sys
import os
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent

def run_command(cmd, description):
    log.info(f"--- Starting: {description} ---")
    log.info(f"Command: {cmd}")
    try:
        env = os.environ.copy()
        # Add backend to path for imports
        env["PYTHONPATH"] = str(BACKEND_ROOT)
        
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=True, 
            cwd=str(BACKEND_ROOT),
            env=env,
            capture_output=False
        )
        log.info(f"--- Completed: {description} ---\n")
    except subprocess.CalledProcessError as e:
        log.error(f"!!! Failed: {description} !!!")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run full training/inference prep pipeline.")
    parser.add_argument(
        "--compress-content-model",
        action="store_true",
        help="Run content embedding compression after native training.",
    )
    args = parser.parse_args()

    log.info("Starting Full Movie Recommendation Pipeline...")

    # 1. Metadata standardization
    run_command("python3 scripts/finalize_metadata.py", "Metadata Standardization")

    # 2. Prepare data and generate features
    run_command("python3 scripts/prepare_data.py", "Data Preparation")

    # 3. Train retrieval + ranker models
    run_command("python3 scripts/run_native_training.py", "Native Training Pipeline")

    # 4. Optional post-training compression for content model artifacts
    if args.compress_content_model:
        run_command(
            "python3 scripts/compress_content_model.py",
            "Content Model Compression",
        )

    log.info("All pipeline steps completed successfully!")

if __name__ == "__main__":
    main()
