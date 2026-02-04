#!/bin/bash
set -e

# Directory of this script (backend/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Paths to binaries
TRAIN_DIR="$DIR/training/retrieval/native"
FEATURE_DIR="$DIR/features/native"
VALIDATE_SCRIPT="$DIR/scripts/validate_native_training.py"
FINALIZE_SCRIPT="$DIR/scripts/finalize_artifacts.py"

# Compile Feature Tools
echo "[Native] Compiling Feature Tools..."
(cd "$FEATURE_DIR" && make)

# Compile Training Tools
echo "[Native] Compiling Training Tools..."
(cd "$TRAIN_DIR" && make)

# Run ALS Pipeline
# 1. Bridge (Parquet -> Binary Stream)
# 2. Matrix Builder (Binary Stream -> Sparse Matrix Binary)
# 3. Train ALS (Sparse Matrix Binary -> Embeddings)
echo "[Native] Running ALS Training Pipeline..."
INPUT_PARQUET="$DIR/data/processed/ratings.parquet"
PROJECT_ROOT="$DIR/.."

echo "Running from Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

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
