# P0 API entrypoint cleanup evidence

## Scope

- Removed `backend/api/main.py`, the duplicate entrypoint that imported missing
  `data_io.data_loader` and `inference.pipeline` modules.
- Added `backend/tests/unit/test_api_entrypoint.py`, which imports the public
  `main` entrypoint and verifies that the obsolete path is absent.
- `backend/main.py` and all API routers are unchanged. The only
  `uvicorn api.main:app` reference was inside the removed file; no non-audit
  documentation required a separate update.

## TDD evidence

RED, before deletion:

```text
UV_CACHE_DIR=/tmp/movie-recs-uv-cache PYTHONPATH=backend uv run --frozen pytest backend/tests/unit/test_api_entrypoint.py -q
FAILED backend/tests/unit/test_api_entrypoint.py::test_active_main_entrypoint_imports_without_duplicate_api_module
AssertionError: assert not True
... /backend/api/main.py).exists
1 failed
```

GREEN, after deletion:

```text
UV_CACHE_DIR=/tmp/movie-recs-uv-cache PYTHONPATH=backend uv run --frozen pytest backend/tests/unit/test_api_entrypoint.py -q
1 passed, 3 warnings
```

## Required verification

```text
UV_CACHE_DIR=/tmp/movie-recs-uv-cache PYTHONPATH=backend uv run --frozen pytest backend/tests/unit -q
59 passed, 6 warnings

git diff --check
exit 0
```

The warnings are pre-existing dependency/deprecation warnings from `faiss`,
FastAPI's `on_event`, and an existing invalid escape sequence in a unit test.
