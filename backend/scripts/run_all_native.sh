#!/bin/bash
set -e

# Directory of this script (backend/scripts/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$DIR/.." && pwd )"

# Paths to binaries
TRAIN_DIR="$BACKEND_DIR/training/retrieval/native"
FEATURE_DIR="$BACKEND_DIR/features/native"
VALIDATE_SCRIPT="$DIR/validate_native_training.py"
FINALIZE_SCRIPT="$DIR/finalize_artifacts.py"

# Compile Feature Tools
echo "[Native] Compiling Feature Tools..."
(cd "$FEATURE_DIR" && make)

# Compile Training Tools
echo "[Native] Compiling Training Tools..."
(cd "$TRAIN_DIR" && make)

# Run ALS Pipeline
echo "[Native] Running ALS Training Pipeline..."
INPUT_PARQUET="$BACKEND_DIR/data/processed/ratings.parquet"
PROJECT_ROOT="$( cd "$BACKEND_DIR/.." && pwd )"

echo "Running from Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Set PYTHONPATH for backend modules
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

python3 "$FEATURE_DIR/bridge.py" "$INPUT_PARQUET" | "$FEATURE_DIR/interaction_matrix_builder" | "$TRAIN_DIR/train_als"

# Run Other Models
echo "[Native] Running TF-IDF..."
(cd "$TRAIN_DIR" && ./train_tfidf)

echo "[Native] Running Content-Based..."
(cd "$TRAIN_DIR" && ./train_content)

echo "[Native] Running Two-Tower..."
(cd "$TRAIN_DIR" && ./train_two_tower)

# Validation
echo "[Native] Validating..."
python3 "$VALIDATE_SCRIPT"

# Finalization (Build Indices)
echo "[Native] Finalizing Artifacts (Building FAISS Indices)..."
python3 "$FINALIZE_SCRIPT"

echo "[Native] All steps completed successfully."