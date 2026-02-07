import subprocess
import logging
import sys
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

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
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=False
        )
        log.info(f"--- Completed: {description} ---\n")
    except subprocess.CalledProcessError as e:
        log.error(f"!!! Failed: {description} !!!")
        sys.exit(1)

def main():
    log.info("Starting Full Movie Recommendation Pipeline...")

    # 1. Data Cleaning
    run_command("python3 backend/data/clean_data.py", "Data Cleaning & Filtering")

    # 2. Sequence Generation (C++ Pipeline)
    run_command("cd backend/features/native && make", "Compiling C++ Tools")
    run_command("python3 backend/features/native/run_sequences.py", "Generating Training Sequences")

    # 3. Train Retrieval Models
    # Using the native training script for completeness
    run_command("bash scripts/run_all_native.sh", "Training Retrieval Models (Native)")

    # 4. Generate Ranking Features (C++ Pipeline)
    run_command("python3 backend/features/native/run_ranker_gen.py", "Generating Ranking Dataset")

    # 5. Train Ranker
    run_command("python3 backend/training/ranker.py", "Training Ranking Model (LightGBM)")

    log.info("All pipeline steps completed successfully!")

if __name__ == "__main__":
    main()