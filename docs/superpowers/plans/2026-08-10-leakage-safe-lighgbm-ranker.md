# Leakage-Safe LightGBM Ranker Implementation Plan

> **For agentic workers:** Execute inline task-by-task with tests. Do not commit; this branch is intentionally uncommitted until user review.

**Goal:** Train and validate a reproducible LightGBM LambdaRank model from immutable ranking feature artifacts without random splitting or target leakage.

**Architecture:** Pack query-contiguous Parquet feature rows into NumPy memmaps and query-group arrays, then pass those arrays to LightGBM. Train only on the inner chronological training artifact and use the already-held-out validation artifact only for early stopping, comparison, and model selection. Metrics are pure functions and tracking wraps the trainer.

**Tech Stack:** Python 3.10, PyArrow, NumPy memmap, LightGBM 3.3.5, MLflow, Ruff, pytest.

## Global Constraints

- Do not read or tune against the final test partition.
- Train and validation feature schema/config/code hashes must match.
- Preserve query-contiguous groups and fail on non-monotonic query IDs.
- Keep temporary packed arrays resumable and bounded by configured disk paths.
- Record all model, input, configuration, Git, metric, and artifact hashes.
- Do not use the legacy S3/random-split ranker scripts.

---

### Task 1: Canonical ranking metrics and training configuration

**Files:**
- Create: `backend/configs/ranking_training.yaml`
- Modify: `backend/evaluation/metrics.py`
- Test: `backend/tests/unit/test_ranking_metrics.py`

**Interfaces:**
- Produces `ndcg_at_k`, `map_at_k`, and `mrr_at_k` pure functions with values in `[0, 1]`.
- Produces a typed ranking-training configuration with explicit seed, model parameters, early stopping, and packed-array directory.

- [x] Write failing metric/config tests for a hand-computed ranked label list and invalid K.
- [x] Implement pure metric helpers and a minimal YAML loader.
- [x] Run Ruff and focused unit tests.

### Task 2: Query-safe feature packer

**Files:**
- Create: `backend/training/ranking/pipeline.py`
- Test: `backend/tests/integration/test_ranking_training_pipeline.py`

**Interfaces:**
- Consumes a feature Parquet file, `feature_schema.json`, and a feature manifest.
- Produces `PackedRankingData(features, labels, groups, query_count, row_count)` backed by deterministic NumPy memmaps.
- Fails if feature schema/config/code hashes differ between train and validation, query IDs are not contiguous, or groups do not sum to rows.

- [x] Write failing fixture tests for group construction, hash mismatch, and ordered feature loading.
- [x] Stream Parquet row groups into memmaps; checkpoint packing state after each row group.
- [x] Run Ruff and focused integration tests.

### Task 3: LightGBM trainer, validation comparison, and artifact manifest

**Files:**
- Modify: `backend/training/ranking/pipeline.py`
- Create: `backend/training/ranking/cli.py`
- Test: `backend/tests/integration/test_ranking_training_pipeline.py`

**Interfaces:**
- Consumes packed train/validation artifacts and the training YAML.
- Produces a model directory with `model.txt`, `manifest.json`, `feature_schema.json`, and machine-readable validation metrics.
- Evaluates retrieval-score ordering and LightGBM ordering using NDCG@5/10, MAP@10, and MRR@10.

- [x] Write a failing deterministic fixture test proving the trainer uses supplied query groups and writes a versioned artifact manifest.
- [x] Train LambdaRank with validation-only early stopping and calculate canonical metrics.
- [x] Track parameters, hashes, row/group counts, and metrics in MLflow.
- [x] Run the small deterministic trainer test, Ruff, and the focused ranking suite.

### Task 4: Full-run evidence and test-boundary documentation

**Files:**
- Modify: `docs/evaluation/EVALUATION_PROTOCOL.md`
- Modify: `docs/superpowers/plans/2026-08-10-ranking-data-pipeline.md`

- [x] Document the exact training/validation artifact paths, compatibility checks, command, and the fact that test remains untouched.
- [ ] Run the full local trainer after fixture verification; retain its generated machine-readable result before reporting any metric.
