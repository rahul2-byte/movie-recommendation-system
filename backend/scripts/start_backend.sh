#!/usr/bin/env bash
set -euo pipefail

echo "Starting FastAPI server..."
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
