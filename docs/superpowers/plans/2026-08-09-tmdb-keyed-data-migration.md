# TMDB-Keyed Data Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the offline dataset reproducible, Parquet-based, and keyed by TMDB IDs without changing the recommendation architecture.

**Architecture:** One deterministic builder replaces the stale CSV converter. It validates raw MovieLens inputs, makes lossless compressed Parquet copies, builds a one-to-one canonical catalog, and joins its TMDB identity into ratings and tags. MovieLens IDs remain lineage fields; `item_index` is the internal dense index.

**Tech Stack:** Python 3.10, pandas, PyArrow, pytest; existing locked dependencies only.

## Global Constraints

- Raw data is never overwritten.
- Use Zstandard compression with level 3.
- `tmdb_id` is the operational key; `movielens_id` is lineage only.
- No DynamoDB/runtime serving change in this data-contract task.
- No commits unless explicitly requested by the user.

---

### Task 1: Specify and test the canonical dataset builder

**Files:**
- Create: `tests/test_csv_to_parquet.py`
- Modify: `backend/scripts/data_enrichment/csv_to_parquet.py`

**Interfaces:**
- Produces: `build_processed_dataset(raw_dir: Path, output_dir: Path, enriched_path: Path) -> dict[str, int]`
- Produces: `DatasetValidationError`

- [x] **Step 1: Write the failing tests**

```python
summary = build_processed_dataset(raw_dir, output_dir, enriched_path)
catalog = pd.read_parquet(output_dir / "catalog.parquet")
assert catalog[["tmdb_id", "movielens_id", "item_index"]].to_dict("records") == [
    {"tmdb_id": 10, "movielens_id": 1, "item_index": 0}
]
assert summary["excluded_ambiguous_tmdb_rows"] == 2
```

- [x] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=backend uv run --frozen pytest tests/test_csv_to_parquet.py -q`

Expected: FAIL because `build_processed_dataset` does not exist.

- [x] **Step 3: Implement the minimal builder**

```python
def build_processed_dataset(raw_dir: Path, output_dir: Path, enriched_path: Path) -> dict[str, int]:
    """Validate sources and write canonical Zstandard Parquet datasets."""
```

The implementation writes source conversions, canonical catalog/interactions,
and a JSON manifest.

- [x] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=backend uv run --frozen pytest tests/test_csv_to_parquet.py -q`

Expected: PASS.

### Task 2: Execute the builder against MovieLens 32M

**Files:**
- Modify: `docs/evaluation/DATASET.md`

**Interfaces:**
- Consumes: `build_processed_dataset(...)`
- Produces: `backend/data/processed/manifest.json` (ignored generated artifact)

- [x] **Step 1: Run the deterministic conversion**

Run: `PYTHONPATH=backend uv run --frozen python backend/scripts/data_enrichment/csv_to_parquet.py`

- [x] **Step 2: Verify Parquet schemas and manifest**

Run: `PYTHONPATH=backend uv run --frozen pytest tests/test_csv_to_parquet.py -q`

- [x] **Step 3: Record only observed conversion facts**

Document commands, output contract, and `NOT YET MEASURED` for recommendation quality.

### Task 3: Migrate Python model artifacts to the canonical key

**Files:**
- Modify: `backend/training/retrieval/*.py`
- Modify: `backend/retrieval/models/*.py`
- Modify: `backend/features/*.py`
- Test: `tests/test_tmdb_id_contract.py`

**Interfaces:**
- Consumes: canonical Parquet files.
- Produces: artifact `tmdb_id_to_idx.json` maps and TMDB-keyed candidates.

- [ ] **Step 1: Write tests proving candidates and feature rows preserve TMDB IDs**
- [ ] **Step 2: Verify they fail against MovieLens-ID behavior**
- [ ] **Step 3: Make Python training/inference use `tmdb_id` plus `item_index` only where array positions are needed**
- [ ] **Step 4: Run focused tests and a small deterministic train/inference fixture**

### Task 4: Replace runtime DynamoDB metadata with TMDB

**Files:**
- Modify: `backend/common/services/movie_store.py`
- Modify: `backend/pipeline/pipeline.py`
- Modify: `backend/api/schemas/recommend.py`
- Modify: `template.yaml`
- Test: `tests/test_tmdb_runtime.py`

**Interfaces:**
- Consumes: `Query(seed_tmdb_ids: list[int])`, TMDB live metadata, S3 model artifacts.
- Produces: TMDB-keyed API recommendations.

- [ ] **Step 1: Write tests for live metadata formatting, unknown-seed handling, and no MovieLens-ID aliases**
- [ ] **Step 2: Verify they fail against the DynamoDB path**
- [ ] **Step 3: Implement TMDB-backed metadata fetches and TMDB-ID API contracts**
- [ ] **Step 4: Remove DynamoDB parameters, IAM permissions, and code only after all runtime tests pass**

### Task 5: Retire or refactor native binaries deliberately

**Files:**
- Modify: `backend/features/native/dump_binary_data.py`
- Modify or delete: native C++ training path after evidence review
- Test: `tests/test_native_id_mapping.py`

**Interfaces:**
- Consumes: `item_index`, never raw TMDB IDs as array offsets.

- [ ] **Step 1: Write an oversized-TMDB-ID fixture test**
- [ ] **Step 2: Verify the current max-ID array behavior fails the contract**
- [ ] **Step 3: Replace it with the dense `item_index` mapping or retire the unused path**
- [ ] **Step 4: Run the native smoke check before retaining it**

## Review Checklist

- [ ] Raw source files remain unchanged.
- [ ] Every operational processed ID is `tmdb_id`.
- [ ] Manifest explains exclusions and compression.
- [ ] No model-quality or performance claim is made without an evaluation artifact.
