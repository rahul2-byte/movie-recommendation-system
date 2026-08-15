#!/usr/bin/env bash
set -euo pipefail

# Local preflight for Lambda container build/runtime.
# Runs the same Dockerfile used by CI and performs a runtime invoke check.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$BACKEND_DIR/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-movie-recs-lambda:local}"
CONTAINER_NAME="${CONTAINER_NAME:-movie-lambda-local}"
LAMBDA_PORT="${LAMBDA_PORT:-9000}"
APP_PORT="${APP_PORT:-8080}"

ENVIRONMENT="${ENVIRONMENT:-PROD}"
MODEL_BUNDLE_PATH="${MODEL_BUNDLE_PATH:-backend/model_bundle/production}"

cd "$ROOT_DIR"

if ! test -f "$MODEL_BUNDLE_PATH/bundle_manifest.json"; then
  echo "ERROR: Model bundle manifest not found: $MODEL_BUNDLE_PATH/bundle_manifest.json" >&2
  exit 1
fi
for required_file in \
  ranker/manifest.json \
  ranker/model.txt \
  ranker/feature_schema.json \
  retrievers/als/manifest.json \
  retrievers/item_graph/manifest.json \
  retrievers/two_tower/manifest.json \
  retrievers/content/manifest.json; do
  if ! test -f "$MODEL_BUNDLE_PATH/$required_file"; then
    echo "ERROR: Required model bundle file not found: $MODEL_BUNDLE_PATH/$required_file" >&2
    exit 1
  fi
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: Required command '$1' is not installed." >&2
    exit 1
  fi
}

cleanup() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

require_cmd docker
require_cmd curl

echo "[1/4] Building Lambda image from backend/Dockerfile.lambda..."
DOCKER_BUILDKIT=0 docker build --no-cache --network=host \
  -t "$IMAGE_NAME" \
  -f backend/Dockerfile.lambda \
  --build-arg MODEL_BUNDLE_PATH=$MODEL_BUNDLE_PATH \
  .

echo "[2/4] Starting Lambda container..."
RUN_ARGS=(
  --rm -d
  --name "$CONTAINER_NAME"
  -p "${LAMBDA_PORT}:${APP_PORT}"
  -e "ENVIRONMENT=${ENVIRONMENT}"
)


docker run "${RUN_ARGS[@]}" "$IMAGE_NAME" >/dev/null

echo "[3/4] Waiting for startup logs..."
sleep 5
docker logs "$CONTAINER_NAME" --tail 200 || true

echo "[4/4] Invoking Lambda runtime endpoint..."
PING_PAYLOAD='{"rawPath":"/ping","requestContext":{"http":{"method":"GET","path":"/ping"}}}'
PING_RESP="$(curl -sS -XPOST "http://localhost:${LAMBDA_PORT}/2015-03-31/functions/function/invocations" -d "$PING_PAYLOAD")"
echo "Response: ${PING_RESP}"

if [[ "$PING_RESP" == *"errorMessage"* ]] || [[ "$PING_RESP" == *"Internal server error"* ]]; then
  echo "ERROR: Lambda invocation failed. Check container logs above." >&2
  exit 1
fi

echo "Preflight passed: build + startup + runtime invoke succeeded."
