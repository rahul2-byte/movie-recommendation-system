# P0 MLflow startup report

## Scope

- Branch: `fix/p0-mlflow-startup`
- Changed: `backend/logger/services/mlflow_logger.py`
- Added: `backend/tests/unit/test_mlflow_logger.py`
- Unchanged: MLflow training integrations and dependency declarations.

## TDD evidence

### RED

Command:

```sh
UV_CACHE_DIR=/tmp/movie-recs-uv-cache uv run --frozen pytest backend/tests/unit/test_mlflow_logger.py -q
```

Result: `3 failed, 1 passed` (exit 1).

- `test_importing_main_does_not_configure_mlflow` failed because import-time
  `logger.services.mlflow_utils.mlflow.set_tracking_uri()` raised the injected
  `RuntimeError("MLflow is unavailable")`.
- `test_logging_hooks_keep_telemetry_in_memory_when_mlflow_setup_fails` failed
  from the same import-time setup.
- `test_failed_flush_preserves_buffered_telemetry` failed because
  `mlflow.start_run()` raised and `flush_to_mlflow()` propagated it.

### GREEN

Implementation moves tracking URI and experiment resolution into the flush
attempt, catches all setup/flush exceptions, retains buffers on failure, and
clears them only after a successful flush. Recommendation traces and latency
lists are capped at 1,000 entries.

Focused command:

```sh
UV_CACHE_DIR=/tmp/movie-recs-uv-cache uv run --frozen pytest backend/tests/unit/test_mlflow_logger.py -q
```

Result: `4 passed` (exit 0). There were three existing dependency/framework
deprecation warnings.

## Final verification

```sh
UV_CACHE_DIR=/tmp/movie-recs-uv-cache uv run --frozen ruff check backend/logger/services/mlflow_logger.py backend/tests/unit/test_mlflow_logger.py
```

Result: `All checks passed!` (exit 0).

```sh
UV_CACHE_DIR=/tmp/movie-recs-uv-cache uv run --frozen pytest backend/tests/unit -q
```

Result: `58 passed` (exit 0), with six existing deprecation warnings from
FAISS, FastAPI startup events, and an invalid escape sequence in an unrelated
test.
