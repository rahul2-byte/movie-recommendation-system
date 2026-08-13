# Leakage-Safe Ranking Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce immutable, TMDB-keyed candidate-ranking datasets that can train and evaluate a LightGBM ranker without reusing future interactions.

**Architecture:** Extend the existing `data_pipeline` rather than revive the legacy feature-generation scripts. An inner chronological split of the current `train.parquet` separates retrieval-model fitting from ranking labels. Retrieval artifacts fitted only on the inner retrieval history generate candidate pools; later positives supply labels. The existing validation and untouched test query files remain the model-selection and final-evaluation partitions.

**Tech Stack:** Python 3.10, pandas, NumPy, PyArrow, YAML, MLflow, existing retrieval artifacts; no new dependencies.

## Global Constraints

- Do not modify or overwrite raw data or an existing immutable dataset version.
- Operational movie identity is `tmdb_id`; `movielens_id` is lineage only.
- Use only rating-3-or-higher, deduplicated positive interactions.
- A ranking query has exactly five chronologically earlier seed IDs.
- A candidate label is derived only from interactions strictly after the query history.
- Candidate retrieval never reads the query's ground truth.
- Do not use `user_id` as a model feature: production has seeds, not a known MovieLens user.
- Do not combine heterogeneous raw retriever scores; retain source rank/presence and normalize source scores within each source only.
- Keep outputs resumable, progress-reporting, hash-manifested, and MLflow-tracked.
- No commit unless explicitly requested by the user.

---

## Current Unsafe Paths to Retire from the Authoritative Workflow

- `backend/training/ranking/train_ranker_v2.py` constructs a `GroupShuffleSplit` over a precomputed file. It is not temporal and therefore is not acceptable for this pipeline.
- `backend/training/ranking/train_ranker.py` downloads an assumed S3 dataset and also performs grouped random splitting. It is not an authoritative local training entry point.
- `backend/features/generate_training_features.py` expects obsolete `ranking_dataset.parquet` fields and calls the current `FeatureBuilder` with an incompatible interface.
- `backend/ranking/inference/lgbm.py` silently fills missing features and falls back to unranked candidates on a feature mismatch. It must not be connected to a new artifact until a versioned feature-schema contract exists.

Retain these files during the migration, but mark them as unsupported in documentation. Do not delete them before the new ranker is trained, evaluated, and integrated.

## Dataset Roles

| Dataset | Purpose | What may fit on it | What it must not influence |
| --- | --- | --- | --- |
| `retrieval_train` | Earlier per-user prefix of current `train.parquet` | ALS, two-tower, item graph, popularity counts | ranking labels, validation, test |
| `ranking_train` | Later per-user events from current `train.parquet` | LightGBM parameters | retriever fitting for the same query |
| `validation.parquet` | Existing held-out query file | model/fusion selection | final system decision |
| `test.parquet` | Existing final held-out query file | final report only | feature/model/fusion selection |

The first implementation uses one inner chronological split. It is the smallest defensible replacement for the legacy random split. Cross-fitted inner folds are a later enhancement if a single inner split proves too data-inefficient.

## Canonical Ranking Row Contract

`ranking_train.parquet` contains one retrieved candidate per `query_index`:

```text
query_index, candidate_tmdb_id, label,
retrieval_als_rank, retrieval_als_score_normalized,
retrieval_item_graph_rank, retrieval_item_graph_score_normalized,
retrieval_two_tower_rank, retrieval_two_tower_score_normalized,
retrieval_source_count
```

The adjacent `ranking_queries.parquet` contains `query_index`, user ID, seed IDs, future targets, and temporal boundaries. `label` is `1` when `candidate_tmdb_id` is in the later positive targets for that query, otherwise `0`. Seed IDs are excluded from candidates. Keeping repeated lists out of candidate rows makes the full dataset practical while preserving provenance through the join key.

The first feature schema will contain only retrieval evidence plus metadata interaction features that can be computed from the immutable catalog:

- source presence, rank, normalized score, and source count;
- candidate popularity computed from `retrieval_train` only;
- seed-to-candidate genre/keyword/text similarity, collection/director/cast overlap, release-year distance, language/country match;
- aggregate seed statistics and known-seed count.

It excludes live TMDB values, MovieLens user IDs, targets, timestamps later than query history, and raw heterogeneous scores.

## Task 1: Add a versioned ranking-data configuration

**Files:**
- Create: `backend/configs/ranking_data.yaml`
- Modify: `backend/data_pipeline/config.py`
- Test: `backend/tests/unit/test_ranking_data_config.py`

**Interfaces:**
- Produces: `RankingDataConfig` loaded from the same repository-relative configuration pattern as `DataPipelineConfig`.
- Required settings: `dataset_version`, `inner_train_fraction`, `seed_count`, `positive_rating_threshold`, `candidate_k`, enabled retrievers, compression, random seed, and MLflow experiment name.

- [x] Write a failing configuration test for valid parsing and invalid fractions/seed counts.
- [x] Run `uv run --frozen pytest backend/tests/unit/test_ranking_data_config.py -q` and confirm it fails because the loader does not exist.
- [x] Add the smallest typed config loader and validate that the inner split leaves at least five seeds plus one target per eligible user.
- [x] Re-run the focused test and format changed Python files with Black.

## Task 2: Build the inner chronological split

**Files:**
- Create: `backend/data_pipeline/ranking.py`
- Modify: `backend/data_pipeline/cli.py`
- Test: `backend/tests/integration/test_ranking_data_pipeline.py`

**Interfaces:**
- Consumes: `<version>/train.parquet` and `RankingDataConfig`.
- Produces: an immutable ranking-data directory beneath the source dataset version containing `retrieval_train.parquet`, `ranking_events.parquet`, and `manifest.json`. Task 3 adds the distinct candidate-labelled `ranking_train.parquet` output.
- Command: `python -m data_pipeline.cli ranking-prepare --dataset-version <id>`.

- [x] Write a fixture test where a user has timestamp ties, verifying train events are strictly earlier than ranking targets and no timestamp is split across the boundary.
- [x] Run the test and confirm it fails because the command/output does not exist.
- [x] Implement per-user chronological inner splitting, deterministic filtering, atomic Parquet writes, resumable completed-output detection, progress reporting, hashes, and an MLflow run.
- [x] Re-run the focused test. Verify output rows are TMDB-keyed and `max(retrieval_train.timestamp) < target_start_timestamp` for every emitted ranking query where the comparison applies.

## Task 3: Generate candidate-labelled ranking rows

**Files:**
- Modify: `backend/data_pipeline/ranking.py`
- Modify: `backend/training/retrieval/cli.py` only if a reusable programmatic artifact-training entry point is missing
- Test: `backend/tests/integration/test_ranking_data_pipeline.py`

**Interfaces:**
- Consumes: retriever artifacts fitted exclusively on `retrieval_train.parquet`, later ranking queries, and the immutable catalog.
- Produces: compact `ranking_train.parquet` and `ranking_queries.parquet`, plus a manifest recording artifact hashes and zero-positive/zero-candidate query counts. The writer checkpoints immutable Parquet parts after each configured query batch and can resume a compatible interrupted generation.

- [x] Write a failing fixture test proving a seed never becomes a candidate, a future target has label `1`, and an unretrieved target is recorded as a retrieval miss rather than fabricated as a negative.
- [x] Run the test and confirm it fails because candidate-labelled output does not exist.
- [x] Train/reuse inner-split ALS, item-graph, and two-tower artifacts through their authoritative Python builders; merge their candidate union by TMDB ID while retaining per-source rank and normalized rank scores.
- [x] Emit only candidates actually retrieved. Record queries with zero candidates and queries with no positive retrieved candidate in the manifest and MLflow metrics.
- [x] Add a fixture interruption/resume test proving completed candidate parts are reused without duplicating queries.
- [ ] Re-run the focused test and a deterministic full-data build.

## Task 4: Lock the first canonical feature schema

**Files:**
- Create: `backend/configs/ranking_features.yaml`
- Create: `backend/training/ranking/features.py`
- Test: `backend/tests/unit/test_ranking_features.py`

**Interfaces:**
- Consumes: canonical candidate-labelled rows, `catalog.parquet`, and popularity statistics from `retrieval_train.parquet`.
- Produces: a feature frame with an ordered, versioned feature list and explicit missing-value rules.

- [x] Write failing tests for deterministic feature order, zero-filled missing metadata, no user-ID feature, and source-score normalization occurring independently per source.
- [x] Run the focused tests and confirm they fail because the feature builder does not exist.
- [x] Implement pure, dataframe-oriented feature construction. Persist `feature_schema.json` containing feature names, order, defaults, dataset version, config hash, and code hash.
- [x] Re-run the focused tests and verify all metric-like feature values are finite.

## Task 5: Produce ranker train/validation inputs and characterize the legacy paths

**Files:**
- Modify: `backend/data_pipeline/ranking.py`
- Modify: `docs/evaluation/EVALUATION_PROTOCOL.md`
- Create: `docs/audit/RANKING_PIPELINE_MIGRATION.md`
- Test: `backend/tests/integration/test_ranking_data_pipeline.py`

**Interfaces:**
- Produces: immutable `ranking_train.parquet` and `ranking_validation.parquet` feature files, their manifest, and MLflow provenance.

- [ ] Write a failing integration test asserting all rows for a `query_id` are contiguous, group sizes sum to row count, and validation uses only the already-held-out validation query targets.
- [ ] Run it and confirm it fails before the final writer is added.
- [ ] Build validation candidate rows from the selected retrieval artifact protocol without fitting on validation targets; apply the same feature-schema version.
- [ ] Write an explicit migration document marking the old ranker scripts and feature generator unsupported—not deleted.
- [ ] Re-run focused tests plus `uv run --frozen pytest backend/tests/unit backend/tests/integration -q` (with the known unrelated `MovieStore` failure documented separately if it still exists).

## Task 6: Evidence check before LightGBM training

**Files:**
- Modify: `docs/evaluation/EVALUATION_PROTOCOL.md`

- [ ] Run the ranking-data CLI on `movielens-32m-76a530585bf1`.
- [ ] Inspect its manifest: source/config/artifact hashes, query counts, candidate counts, retrieval-positive rate, zero-positive groups, group-size distribution, and feature-schema version.
- [ ] Record the exact command and generated artifact paths. Do not claim ranker uplift until a separate LightGBM training and end-to-end held-out evaluation stage completes.

## Verification Criteria

- Every ranker-training candidate is retrieved from a model fitted only on chronologically earlier data for that query.
- No seed ID appears as a candidate; no candidate/target label is inferred from non-positive or future-visible data.
- Outputs are immutable, resumable, hashed, reproducible with a fixed configuration and seed, and tracked in MLflow.
- Validation and test semantics remain unchanged and test is not used for model selection.
- The feature schema is versioned, ordered, and compatible with future serving validation.

## Deliberately Deferred

- LightGBM model fitting, hyperparameter selection, and ranking metrics.
- Cross-fitted temporal folds.
- Live TMDB metadata or online evaluation.
- Runtime ranker integration and feature/artifact compatibility enforcement.

Those are subsequent phases; they must consume the verified ranking-data contract rather than bypass it.
