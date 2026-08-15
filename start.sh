#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="$ROOT_DIR/backend/data/raw"
DATASET_URL="https://files.grouplens.org/datasets/movielens/ml-32m.zip"
CHECKSUM_URL="https://files.grouplens.org/datasets/movielens/ml-32m.zip.md5"
TEMP_DIR=""

cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}
trap cleanup EXIT

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: Required command '$1' is not installed." >&2
    exit 1
  fi
}

md5_file() {
  if command -v md5sum >/dev/null 2>&1; then
    md5sum "$1" | awk '{print $1}'
  else
    md5 -q "$1"
  fi
}

dataset_is_valid() {
  local filename expected actual
  while read -r filename expected; do
    [[ -f "$RAW_DIR/$filename" ]] || return 1
    actual="$(md5_file "$RAW_DIR/$filename")"
    [[ "$actual" == "$expected" ]] || return 1
  done <<'EOF'
links.csv 8f033867bcb4e6be8792b21468b4fa6e
movies.csv 0df90835c19151f9d819d0822e190797
ratings.csv cf12b74f9ad4b94a011f079e26d4270a
tags.csv 963bf4fa4de6b8901868fddd3eb54567
EOF
}

for command_name in uv node npm curl unzip awk; do
  require_command "$command_name"
done
if ! command -v md5sum >/dev/null 2>&1 && ! command -v md5 >/dev/null 2>&1; then
  echo "ERROR: Required command 'md5sum' or 'md5' is not installed." >&2
  exit 1
fi

echo "[1/3] Installing locked Python dependencies..."
(cd "$ROOT_DIR" && uv sync --frozen)

echo "[2/3] Installing locked frontend dependencies..."
npm ci --prefix "$ROOT_DIR/frontend"

echo "[3/3] Preparing MovieLens 32M..."
mkdir -p "$RAW_DIR"
if dataset_is_valid; then
  echo "MovieLens 32M is already present and verified."
else
  TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/movie-recs-bootstrap.XXXXXX")"
  archive="$TEMP_DIR/ml-32m.zip"
  checksum_file="$TEMP_DIR/ml-32m.zip.md5"
  extract_dir="$TEMP_DIR/extracted"

  echo "Downloading MovieLens 32M archive (about 228 MiB); progress follows:"
  curl --fail --location --show-error --progress-bar --output "$archive" "$DATASET_URL"
  curl --fail --location --show-error --silent --output "$checksum_file" "$CHECKSUM_URL"

  expected_archive_md5="$(awk 'NR == 1 {print $1}' "$checksum_file")"
  actual_archive_md5="$(md5_file "$archive")"
  if [[ ! "$expected_archive_md5" =~ ^[[:xdigit:]]{32}$ ]] ||
    [[ "$actual_archive_md5" != "$expected_archive_md5" ]]; then
    echo "ERROR: MovieLens 32M archive checksum verification failed." >&2
    exit 1
  fi

  mkdir -p "$extract_dir"
  unzip -q "$archive" -d "$extract_dir"
  extracted_dataset="$extract_dir/ml-32m"
  for filename in links.csv movies.csv ratings.csv tags.csv README.txt; do
    if [[ ! -f "$extracted_dataset/$filename" ]]; then
      echo "ERROR: MovieLens archive is missing required file '$filename'." >&2
      exit 1
    fi
  done

  for filename in links.csv movies.csv ratings.csv tags.csv; do
    install -m 0644 "$extracted_dataset/$filename" "$RAW_DIR/$filename"
  done
  install -m 0644 "$extracted_dataset/README.txt" "$RAW_DIR/README.txt"

  if ! dataset_is_valid; then
    echo "ERROR: Installed MovieLens 32M files failed verification." >&2
    exit 1
  fi
  echo "MovieLens 32M downloaded and verified."
fi

echo "Python environment: $ROOT_DIR/.venv"
echo "Dataset: $RAW_DIR"
echo "Setup complete. No pipeline or service was started."
