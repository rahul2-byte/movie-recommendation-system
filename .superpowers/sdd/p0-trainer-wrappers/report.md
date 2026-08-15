# P0 retrieval trainer wrappers

- Verified the active retrieval CLI imports the canonical `build_als.py`,
  `build_two_tower.py`, `build_tfidf.py`, and `build_item_graph.py` modules.
- Removed obsolete, broken Python wrappers: `train_als.py`,
  `train_two_tower.py`, and `build_content.py`.
- Added a focused unit regression that preserves the canonical entrypoints and
  rejects the retired wrapper files.
- RED: `test_retrieval_trainer_wrappers.py` failed while `train_als.py` existed.
- GREEN: `UV_CACHE_DIR=/tmp/movie-recs-uv-cache PYTHONPATH=backend uv run --frozen pytest backend/tests/unit -q` passed: 60 tests.
- `git diff --check` passed.
