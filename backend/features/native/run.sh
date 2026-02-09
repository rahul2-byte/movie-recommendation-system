#!/bin/bash
set -e

# Directory of this script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$DIR/../../.."

# Output files
STATS_CSV="$ROOT_DIR/backend/data/processed/training_features.csv"
SEQUENCE_CSV="$ROOT_DIR/backend/data/processed/training_sequences.csv"
INPUT_PARQUET="$ROOT_DIR/backend/data/processed/ratings.parquet"

echo "[Native Pipeline] Starting..."

# 1. Compile C++ if needed
echo "[Native Pipeline] Compiling C++ tools..."
(cd "$DIR" && make)

# 2. Run Pipeline 1: Stats Processor (Pointwise)
# echo "[Native Pipeline] Generating Pointwise Stats..."
# python3 "$DIR/bridge.py" "$INPUT_PARQUET" | "$DIR/processor" > "$STATS_CSV"
# echo "[Native Pipeline] Stats saved to: $STATS_CSV"

# 3. Run Pipeline 2: Sequence Builder (Listwise/Query)
echo "[Native Pipeline] Generating Sequence Training Data (5-Movie Query)..."
# Uses the same bridge (same binary format)
python3 "$DIR/bridge.py" "$INPUT_PARQUET" | "$DIR/sequence_builder" >"$SEQUENCE_CSV"

echo "[Native Pipeline] Done! Sequences saved to: $SEQUENCE_CSV"
ls -lh "$SEQUENCE_CSV"

