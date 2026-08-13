# Project Audit

> **Historical baseline:** This document records the read-only audit performed
> on 2026-08-09. It preserves evidence and counts from that repository state.
> Current implementation and cleanup status are documented in
> `docs/audit/LEGACY_CODE_AUDIT.md` and the architecture documents.

## Audit scope and evidence boundary

- Audit date: 2026-08-09
- Audited repository: `rahul2-byte/movie-recommendation-system`
- Audited commit: `ce631cfa87df35c63f40f183be2c3f594644ce3f`
- Working branch: `chore/local-uv-bootstrap`
- Live GitHub default branch observed during the audit: `Main`
- Local `origin/HEAD`: `refs/remotes/origin/Main`
- Python source parsed: 90 files, 0 syntax errors

This is a static and read-only Phase 0 audit. The repository does not contain the
MovieLens CSV/Parquet files or generated model artifacts required to execute the
full pipeline. No training, evaluation, serving benchmark, deployment, or model
quality claim was therefore verified. Those capabilities are marked **UNVERIFIED**
or **NOT YET MEASURED**, not working.

## Executive assessment

The repository has a coherent intended serving architecture: a Next.js frontend
calls a FastAPI application deployed through API Gateway and Lambda; the backend
loads movie metadata from DynamoDB, retrieval/ranking artifacts from S3, retrieves
candidates with four sources, builds runtime features, and ranks with LightGBM.

The scientific and reproducibility path is not yet production-defensible. There is
no offline evaluation package, no baseline comparison, no temporal train/validation/
test protocol, no ablation evidence, no saved quality or latency results, and no ML
regression gate. Several offline Python training entrypoints reference classes or
methods that do not exist. The native path is the closest thing to an authoritative
training path, but it overlaps with stale Python paths, uses a random query split,
has feature-contract risks, relies on undeclared native build requirements, and has
not been executed in this audit.

The smallest defensible approach is to repair and validate one authoritative path,
then build evaluation around it. Adding more recommenders or infrastructure is not
necessary.

## Current architecture

### Online serving path

1. `backend/main.py` exposes the FastAPI application and Lambda handler.
2. `backend/common/lifecycle.py` lazily creates `MovieStore`, `RecallService`,
   `FeatureBuilder`, and `LGBMRanker`.
3. `backend/pipeline/pipeline.py` fetches seed metadata, recalls up to 500
   candidates, fetches candidate metadata, builds features, ranks, and formats the
   response.
4. `backend/retrieval/inference/recall.py` initializes TF-IDF, content-based, ALS,
   and two-tower retrievers concurrently at request time.
5. Each retriever downloads embeddings, a FAISS index, and an ID map from fixed S3
   keys through `S3ArtifactRepository`.
6. `backend/ranking/inference/lgbm.py` downloads and loads a LightGBM model from S3.
7. Movie metadata is read from DynamoDB, with TMDB/OMDb enrichment paths available.

### Offline path currently implied by the repository

1. MovieLens CSVs are expected under `backend/data/raw/`.
2. `backend/scripts/data_enrichment/csv_to_parquet.py` validates four raw schemas
   and writes Parquet files to `backend/data/processed/`.
3. External metadata enrichment is expected to produce
   `movies_enriched.parquet`.
4. `backend/scripts/run_full_pipeline.py` calls metadata finalization, native data
   preparation, and `run_native_training.py`.
5. The native path generates temporal five-seed windows, ranking features, native
   retrieval outputs, a LightGBM model, and runtime FAISS artifacts.
6. `backend/scripts/upload_artifacts.py` uploads the contents of
   `backend/artifacts/models/` to fixed S3 keys under `artifacts/models/`.

This flow is inferred from code. End-to-end execution is **UNVERIFIED**.

## Required Phase 0 questions

| Question | Audit result |
|---|---|
| 1. Data source/version | `backend/data/raw/README.txt` identifies MovieLens 32M (`ml-32m`), generated 2023-10-13, with 32,000,204 ratings, 2,000,072 tags, 87,585 movies, and 200,948 users. The actual CSVs are absent, so their identity/checksums are unverified. |
| 2. Required data files | Raw: `movies.csv`, `ratings.csv`, `tags.csv`, `links.csv`. Processed: `movies.parquet`, `ratings.parquet`, `tags.parquet`, `links.parquet`, `movies_enriched.parquet`; later steps also require sequences, ranking data, and binary caches. |
| 3. Authoritative training path | No explicit authority is documented. `run_full_pipeline.py` selects `run_native_training.py`, making the native path the de facto candidate, while multiple conflicting Python/native entrypoints remain. |
| 4. Trainable from scratch | **UNVERIFIED.** The Python ALS, TF-IDF, content, and two-tower entrypoints are statically broken. Native sources exist for all four retrievers and ranking, but require data and native libraries that were not available/executed. |
| 5. Loadable for inference | Loaders exist for four FAISS retrievers and LightGBM. Actual loading is **UNVERIFIED** because artifacts/S3 access are absent. Retriever load failures are converted to empty retrievers; ranker load failure prevents pipeline initialization. |
| 6. Stale/dead/broken scripts | Confirmed broken: Python retrieval trainers/builders and `generate_training_features.py`. Conflicting/likely stale: three ranker trainers, two native training orchestrators, committed duplicate binaries. See findings. |
| 7. Artifact flow | Native output -> `finalize_artifacts.py` -> `backend/artifacts/models/<model>/` -> `upload_artifacts.py` -> fixed S3 keys -> runtime download to `/tmp/movie_artifacts`. A manifest is uploaded but not validated by serving. |
| 8. FAISS reproducibility | Index construction is deterministic for identical ordered embeddings/IDs, using normalized `IndexFlatIP`. Upstream native two-tower training is not deterministic, and source dataset/artifact hashes are not persisted with runtime artifacts. Overall reproducibility is not established. |
| 9. Training/serving features | Feature names mostly overlap, but there is no executable parity test. The Python batch path calls nonexistent APIs; native training and Python serving implement features independently; serving silently fills missing features with zero. |
| 10. Model/feature schema versioning | Raw/enrichment data schemas have versions. Model and ranker feature compatibility metadata are not persisted or checked at load time. |
| 11. Evaluation code | No reusable offline recommendation evaluation exists. Only LightGBM internal NDCG and artifact-shape smoke checks exist. |
| 12. Backend ML tests | No backend test suite exists. `run_tests.py` checks file presence/basic shapes; `run_mini_test.py` mutates config and runs destructive cleanup. No metric, leakage, fusion, parity, API, or failure-mode tests exist. |
| 13. Tests before deployment | No. The workflow configures AWS, builds, pushes, and deploys without lint, tests, ML smoke evaluation, or artifact validation. |
| 14. CI/default branch match | No. GitHub's default branch is `Main`; `.github/workflows/deploy.yml` filters pushes to lowercase `main`. Automatic push deployment therefore does not match the default branch. |

## Findings

### P0 — correctness, invalid evaluation, or broken pipeline

#### P0-01 — No valid offline evaluation or held-out test protocol

- **Evidence:** No `backend/evaluation/` package or implementations of Recall@K,
  HitRate@K, MAP@K, end-to-end NDCG, baselines, retriever contribution, fusion
  experiments, or ablations were found. Repository-wide metric search only found
  LightGBM training NDCG and logging field names.
- **Affected files:** `backend/`, `README.md`
- **Consequence:** There is no evidence that the system beats popularity, that the
  ranker helps, or that any retriever is justified. Model regressions cannot be
  detected.
- **Recommended correction:** Define a temporal train/validation/test protocol
  first, then add pure metric functions, popularity and component baselines, and
  machine-readable reports.
- **Necessary for this project:** Yes.

#### P0-02 — Ranker model selection uses a random split called test

- **Evidence:** `backend/training/ranking/native/converter.cpp:72-78` randomly
  shuffles query windows into an 80/20 split. `train_from_csv.py:21-53` names the
  second partition `test` and uses it for early stopping. The two Python trainers
  also use `GroupShuffleSplit` (`train_ranker.py:62-71`,
  `train_ranker_v2.py:31-39`). None defines a final untouched test partition.
- **Affected files:** `backend/training/ranking/native/converter.cpp`,
  `backend/training/ranking/train_from_csv.py`, `train_ranker.py`,
  `train_ranker_v2.py`
- **Consequence:** Future and past windows from the same user can cross partitions,
  and the reported internal validation metric is not an unbiased test estimate.
- **Recommended correction:** Split source interactions temporally before fitting
  retrieval/ranking components; create separate train, validation, and final test
  partitions; use validation only for early stopping/model selection.
- **Necessary for this project:** Yes.

#### P0-03 — Python retrieval training entrypoints reference nonexistent builders

- **Evidence:** `train_two_tower.py` imports `TwoTowerBuilder`, `train_als.py`
  imports `ALSBuilder`, `build_tfidf.py` imports `TFIDFBuilder`, and
  `build_content.py` imports `ContentBasedBuilder`. None of those classes exists in
  the respective model modules. `tfidf.py:14-15` explicitly says its builder was
  removed.
- **Affected files:** `backend/training/retrieval/*.py`,
  `backend/retrieval/models/*.py`
- **Consequence:** These documented-looking paths cannot train models and obscure
  which implementation is supported.
- **Recommended correction:** Declare the native path authoritative if it passes
  clean-room verification, then remove or quarantine broken Python entrypoints.
  Do not rebuild duplicate trainers unless the native path is intentionally retired.
- **Necessary for this project:** Yes.

#### P0-04 — Python batch feature generation is not executable

- **Evidence:** `generate_training_features.py:35` calls
  `FeatureBuilder.from_paths`, which does not exist; `FeatureBuilder` only provides
  `from_dataframe`. It then calls `build_features(df_raw)`, while the implemented
  signature requires separate seed and candidate metadata lists.
- **Affected files:** `backend/features/generate_training_features.py`,
  `backend/features/builder.py`
- **Consequence:** The claimed shared Python training/serving feature path is broken.
- **Recommended correction:** Remove this dead path if native feature generation is
  retained, or make it a thin batch adapter over the canonical serving feature
  implementation. Add a parity fixture before choosing either.
- **Necessary for this project:** Yes.

#### P0-05 — Ranking feature compatibility can fail silently

- **Evidence:** `backend/ranking/inference/lgbm.py:62-76` fills missing configured
  features with zero and returns unranked candidates on feature-count mismatch.
  It does not compare LightGBM feature names/order, schema version, model version,
  dataset version, or artifact manifest.
- **Affected files:** `backend/ranking/inference/lgbm.py`,
  `backend/features/builder.py`, `backend/configs/features.yml`
- **Consequence:** A mismatched model may silently serve degraded or semantically
  incorrect ordering.
- **Recommended correction:** Persist a canonical ordered feature schema with the
  model and fail application initialization with an actionable compatibility error.
- **Necessary for this project:** Yes.

#### P0-06 — Negative labels are not reliably valid

- **Evidence:** The Python dataset builder creates a global negative pool from
  movies never appearing in any positive interaction (`data/builder.py:71-75`),
  rather than movies unobserved by each user. The native sequence builder samples
  from all movies and explicitly does not check user history
  (`sequence_builder.cpp:136-145`).
- **Affected files:** `backend/data/builder.py`,
  `backend/features/native/sequence_builder.cpp`
- **Consequence:** Python negatives are an unusually biased subset; native negatives
  can be false negatives. Both can distort ranker training and evaluation.
- **Recommended correction:** Define labels and per-user candidate eligibility in
  the evaluation protocol; sample negatives only from items not observed before the
  prediction cutoff, and keep evaluation candidate construction separate from
  training sampling.
- **Necessary for this project:** Yes.

### P1 — major credibility or production issue

#### P1-01 — Raw heterogeneous retrieval scores are fused by maximum

- **Evidence:** `backend/retrieval/inference/recall.py:88-105` stores each source
  score and sets the candidate score to `max(c.score, score)`. ALS, normalized
  cosine/IP, sparse TF-IDF, and two-tower outputs have no demonstrated calibration
  or shared distribution.
- **Affected files:** `backend/retrieval/inference/recall.py`, all retrievers
- **Consequence:** The source with the numerically largest score scale can dominate;
  maximum raw score is not statistically defensible without validation.
- **Recommended correction:** Preserve the current method as a baseline and compare
  it on validation data with reciprocal-rank fusion and per-source normalization.
  Select the smallest approach supported by measured quality/latency.
- **Necessary for this project:** Yes.

#### P1-02 — Retriever contribution and failure behavior are unmeasured

- **Evidence:** All four retrievers are always initialized. Per-retriever exceptions
  return empty lists, but no failure count reaches the response/metric layer and no
  overlap, unique recall, cold-start coverage, or ablation results exist.
- **Affected files:** `backend/retrieval/inference/recall.py`,
  `backend/pipeline/pipeline.py`
- **Consequence:** Complexity and latency cannot be justified, and silent component
  degradation may go unnoticed.
- **Recommended correction:** Add per-source counts/failures/latency to structured
  results and run controlled retriever ablations.
- **Necessary for this project:** Yes.

#### P1-03 — Training authority is ambiguous and duplicated

- **Evidence:** The repository contains `run_native_training.py`,
  `run_all_native.sh`, two native Makefiles, compiled binaries in three locations,
  four broken Python retriever entrypoints, and three ranker trainers with different
  data locations and split behavior.
- **Affected files:** `backend/scripts/`, `backend/training/`,
  `backend/features/native/`, `backend/retrieval/models/`
- **Consequence:** Independent engineers cannot know which path regenerates deployed
  artifacts; fixes can land in an unused implementation.
- **Recommended correction:** Verify one end-to-end path, document it as
  authoritative, and delete or clearly quarantine superseded entrypoints/binaries.
- **Necessary for this project:** Yes.

#### P1-04 — Native build and two-tower training are not reproducible

- **Evidence:** Makefiles depend on `CONDA_PREFIX`, Arrow, Parquet, Armadillo,
  OpenMP, and CPU-specific `-march=native`, but these requirements are not captured
  by the Python dependency files. The two-tower trainer initializes Armadillo random
  weights without an explicit Armadillo seed and uses race-prone Hogwild OpenMP
  updates (`train_two_tower.cpp:89-105`, `206-235`).
- **Affected files:** `backend/training/Makefile`, native sources,
  `environment.yml`, `backend/requirements.txt`
- **Consequence:** Clean-machine builds are platform-dependent, and identical runs
  may produce different embeddings despite a fixed shuffle seed.
- **Recommended correction:** During the planned refactor, first decide whether the
  native path is retained. If retained, document/version its toolchain and test
  multi-seed variance; otherwise remove it only after replacement parity is proven.
- **Necessary for this project:** Yes, if native training remains supported.

#### P1-05 — Dataset identity is documented but not reproducibly acquired

- **Evidence:** Only the MovieLens 32M README is tracked. Required CSVs are absent.
  The README contains per-file MD5 values, but no repository bootstrap verifies the
  archive/source/checksums. Enriched metadata also depends on external APIs and has
  no immutable snapshot/version in the training manifest.
- **Affected files:** `backend/data/raw/README.txt`, data/enrichment scripts,
  project documentation
- **Consequence:** The actual data used for any future result cannot yet be proven
  identical or regenerated.
- **Recommended correction:** Add the already-approved local bootstrap download with
  a fixed official MovieLens 32M URL and checksum validation; record raw and derived
  dataset hashes in evaluation/model metadata.
- **Necessary for this project:** Yes.

#### P1-06 — Artifact publishing uses mutable fixed keys without serving validation

- **Evidence:** `upload_artifacts.py` uploads to `artifacts/models/...` and overwrites
  `manifest.json`. The manifest records Git commit and MD5 checksums, but runtime
  loaders request fixed keys and never read or validate it. Upload failure can also
  fall back to dry-run while the script later reports successful simulated uploads.
- **Affected files:** `backend/scripts/upload_artifacts.py`,
  `backend/common/storage/repositories.py`, `backend/configs/system.yml`
- **Consequence:** A partially incompatible artifact set can replace the prior set;
  serving cannot prove which dataset/code/schema produced loaded files.
- **Recommended correction:** Validate a complete versioned manifest before
  activation and load one immutable artifact version as a set. Keep core evaluation
  independent of S3.
- **Necessary for this project:** Yes before production-defensible deployment.

#### P1-07 — No meaningful automated backend ML tests

- **Evidence:** No `tests/` package exists. `run_tests.py` only checks artifact
  existence/basic shapes. `run_mini_test.py` rewrites `system.yml` in place and runs
  recursive cleanup commands before training.
- **Affected files:** `backend/scripts/run_tests.py`,
  `backend/scripts/run_mini_test.py`, repository test layout
- **Consequence:** Metric correctness, leakage prevention, fusion, feature parity,
  failure degradation, and API contracts can regress undetected.
- **Recommended correction:** Add a small deterministic fixture and focused unit/
  integration tests for the critical ML contracts; replace config mutation with
  injected paths or a temporary config.
- **Necessary for this project:** Yes.

#### P1-08 — Deployment bypasses verification and targets the wrong branch name

- **Evidence:** `.github/workflows/deploy.yml:5-10` filters lowercase `main`, while
  the live GitHub repository and `origin/HEAD` use `Main`. Its only job immediately
  configures AWS, builds/pushes an image, and deploys; it runs no tests or smoke
  evaluation.
- **Affected files:** `.github/workflows/deploy.yml`
- **Consequence:** Default-branch pushes do not match the automatic deployment
  filter, while manual deployment can publish unverified code.
- **Recommended correction:** Add verification jobs first, make deploy depend on
  them, then change the filter to the verified default branch without altering
  deployment semantics.
- **Necessary for this project:** Yes.

#### P1-09 — Python dependency definitions conflict and are not locked

- **Evidence:** `environment.yml` specifies GPU/CUDA FAISS and additional packages;
  `backend/requirements.txt` specifies CPU FAISS, an x86-64 CPython 3.10 PyTorch URL,
  and mostly unpinned packages. Docker consumes only the requirements file. There is
  no root `pyproject.toml` or lock file.
- **Affected files:** `environment.yml`, `backend/requirements.txt`, both backend
  Dockerfiles, README files
- **Consequence:** Local, training, and deployment environments can resolve different
  or incompatible dependencies.
- **Recommended correction:** Complete the approved migration to one root
  `pyproject.toml` and `uv.lock`, verify Docker/local parity, then remove legacy
  manifests. Treat native system libraries separately after the native-path decision.
- **Necessary for this project:** Yes.

#### P1-10 — Model loading policy is inconsistent and can hide retrieval outages

- **Evidence:** Each retriever catches any artifact-load exception and becomes an
  empty retriever; the ranker raises during lifecycle initialization. There is no
  minimum viable retriever policy, artifact-set compatibility check, or surfaced
  failed-retriever count.
- **Affected files:** `backend/retrieval/models/*.py`,
  `backend/common/lifecycle.py`, `backend/retrieval/inference/recall.py`
- **Consequence:** The API may serve from an unknown subset of retrievers or fail
  completely depending on which artifact is missing.
- **Recommended correction:** Define explicit required/optional components, validate
  the artifact set at startup, and expose structured degraded-mode information.
- **Necessary for this project:** Yes.

### P2 — valuable engineering improvement

#### P2-01 — Existing timing logs are not a reproducible benchmark

- **Evidence:** Pipeline/retriever stages log durations and the MLflow logger names
  P50/P95 fields, but there is no repeatable load command, request fixture,
  environment capture, raw samples, or generated latency artifact.
- **Affected files:** `backend/pipeline/pipeline.py`,
  `backend/retrieval/inference/recall.py`, logger services
- **Consequence:** P50/P95/P99, throughput, concurrency, candidate-count, and cold/
  warm behavior are **NOT YET MEASURED**.
- **Recommended correction:** After functional verification, add one local benchmark
  command using an established load tool and label its results `LOCAL BENCHMARK`.
- **Necessary for this project:** Yes for the stated performance objective, but after
  scientific correctness.

#### P2-02 — Data schemas are partial and validation is not a dataset profile

- **Evidence:** Raw column names/dtypes are validated, and enrichment schema versions
  exist. Validation does not check dataset hash/version, allowed ratings, timestamp
  range, duplicates, ID integrity, null policy, sparsity, or minimum history.
- **Affected files:** `backend/configs/schemas/`,
  `backend/scripts/data_enrichment/validate.py`
- **Consequence:** Malformed or wrong-version data can proceed into training.
- **Recommended correction:** Add deterministic dataset validation and generate
  `artifacts/evaluation/dataset_profile.json` plus `docs/evaluation/DATASET.md` from
  the actual downloaded data.
- **Necessary for this project:** Yes.

#### P2-03 — Committed native binaries are not portable provenance

- **Evidence:** Multiple tracked ELF x86-64 executables are stored under feature and
  training directories alongside source. Build IDs differ between duplicate paths,
  and no compiler/library provenance accompanies them.
- **Affected files:** `backend/features/native/*` executables,
  `backend/training/bin/*`, `backend/training/retrieval/native/*` executables
- **Consequence:** A clone can accidentally execute opaque platform-specific outputs
  instead of rebuilding reviewed source.
- **Recommended correction:** Once the authoritative native workflow is decided,
  build binaries from source and ignore generated executables; do not change this
  before native dependency/refactor decisions are made.
- **Necessary for this project:** Recommended if native code remains.

#### P2-04 — README capability language is ahead of measured evidence

- **Evidence:** README describes production-safe lifecycle, accurate re-ranking,
  scalable hosting, and deployed production architecture, but the repository has no
  saved quality, reliability, or latency evidence and deployment was not verified in
  this audit.
- **Affected files:** `README.md`, `backend/README.md`
- **Consequence:** Interviewers cannot distinguish intended architecture from
  executed evidence.
- **Recommended correction:** Preserve the architecture explanation but add measured
  results, reproduction commands, and explicit limitations only after experiments
  run; qualify deployment statements until independently verified.
- **Necessary for this project:** Yes before final reporting.

### P3 — optional enhancement

#### P3-01 — Search path may require a production data-access decision

- **Evidence:** `DynamoDBMovieRepository.search_movies` scans up to 100,000 items with
  a contains filter.
- **Affected files:** `backend/common/storage/repositories.py`
- **Consequence:** Search latency/cost may grow with catalog size, but no benchmark
  currently proves this is a bottleneck.
- **Recommended correction:** Measure first. Replace only if search SLOs fail; this is
  outside the recommendation-validity critical path.
- **Necessary for this project:** No.

## Suspicious-area conclusions

### A/B. Score comparability and maximum-score fusion

Raw scores are not demonstrated to be comparable. TF-IDF, content, and two-tower
queries are normalized before inner-product FAISS search; ALS query normalization is
not performed in its retriever, although finalized item vectors are normalized.
Maximum raw score therefore combines different semantics and distributions. It must
remain only as the current baseline until compared against rank-based and normalized
fusion on validation data.

### C. Python two-tower path

The Python path is statically broken because `TwoTowerBuilder` does not exist. Its
configuration references are also inconsistent: training reads
`config.retrieval.two_tower`, while the available parameters live under
`config.system.retrieval_params.two_tower`. This path is not executable as written.

### D. Native and Python overlap

They overlap and conflict. The full-pipeline orchestrator selects native training,
while Python entrypoints remain present but broken. Native implementations generate
the runtime artifacts currently expected by serving after finalization. The native
path should be treated as the candidate authority, not declared working, until a
clean-data end-to-end run succeeds.

### E. Ranking split and temporal information

MovieLens 32M includes interaction timestamps. Sequence generation already sorts
each user's liked history by timestamp, so a leakage-resistant temporal evaluation
is feasible. The later random query split discards that advantage. The corrected
protocol should define prediction cutoffs before model fitting and ensure held-out
targets are never available to retrieval training, feature aggregation, negative
sampling, or model selection.

### F. Default branch and Actions filter

The live GitHub repository displays `Main`, and local remote metadata agrees. The
workflow listens to lowercase `main`. They do not match.

## Script disposition

| Path | Status | Evidence-based disposition |
|---|---|---|
| `backend/scripts/run_full_pipeline.py` | Candidate orchestrator, unverified | Keep temporarily; use it as the single top-level candidate during clean-room verification. |
| `backend/scripts/run_native_training.py` | Candidate authoritative training path, unverified | Keep temporarily; repair only failures demonstrated during execution. |
| `backend/scripts/run_all_native.sh` | Overlapping orchestration | Defer removal until the candidate path is verified and any unique behavior is reconciled. |
| `backend/training/retrieval/*.py` | Confirmed broken | Remove/quarantine after authority decision; do not repair four duplicate builders by default. |
| `backend/features/generate_training_features.py` | Confirmed broken | Remove or replace with a thin canonical adapter after parity design. |
| `backend/training/ranking/train_ranker.py` | Conflicting S3/random-split path | Do not use for evidence; reconcile after selecting one ranker path. |
| `backend/training/ranking/train_ranker_v2.py` | Conflicting local/random-split path | Do not use for evidence; reconcile after selecting one ranker path. |
| `backend/training/ranking/train_from_csv.py` | Native path ranker trainer, invalid test naming/use | Candidate to retain after temporal train/validation/test correction. |
| `backend/scripts/run_tests.py` | Artifact presence smoke check | Keep only as a smoke check; it is not a test suite or quality evaluation. |
| `backend/scripts/run_mini_test.py` | Unsafe mutable smoke path | Replace with a temporary-fixture integration test; do not run on a dirty worktree. |

## Data risks and limitations

- The actual MovieLens files are absent; dataset counts in this audit come from the
  tracked upstream README, not an inspected dataset.
- The raw README provides file MD5 checksums, but no current project command enforces
  them.
- Metadata enrichment uses mutable external services. Without a snapshot/hash, the
  same MovieLens input can produce different derived metadata later.
- Popularity, vote averages, IMDb values, and TMDB values need cutoff semantics; if
  current metadata is used to evaluate historical targets, it can introduce future
  information.
- Native sequence negatives may be known user positives. Python negatives have a
  different and strongly biased definition.
- MovieLens offline relevance does not establish user engagement or online business
  impact.

## Minimal implementation plan

The order below intentionally repairs evidence foundations before optimizing or
expanding the system.

1. **Bootstrap and dependency authority**
   - Add root `pyproject.toml` and `uv.lock` as the sole Python dependency source.
   - Add the approved local script that prepares the UV environment and downloads
     the fixed MovieLens 32M dataset with checksum validation.
   - Keep frontend npm/`package-lock.json`; remove legacy manifests only after parity.
   - Defer native dependency removal or replacement until the native path is tested.

2. **Dataset validation and profile**
   - Validate the actual downloaded files and checksums.
   - Generate the required JSON and Markdown dataset profile.
   - Assign a deterministic dataset version/hash to derived data.

3. **Evaluation protocol before model work**
   - Define temporal train/validation/test cutoffs and seed construction.
   - Add leakage and determinism tests.
   - Keep test data untouched until the final system choice.

4. **Metric primitives and simple baseline**
   - Implement tested Recall@K, HitRate@K, Precision@K, NDCG@K, and MAP@K.
   - Evaluate global popularity first.

5. **One authoritative training/artifact path**
   - Execute the native candidate path on a deterministic small fixture.
   - Fix only demonstrated blockers.
   - Remove/quarantine duplicate broken paths after parity is established.
   - Version the feature schema and artifact manifest; fail fast on mismatch.

6. **Retriever, fusion, and ranker evidence**
   - Evaluate each retriever and current max-score fusion.
   - Compare RRF and normalized fusion on validation data.
   - Evaluate ranker ordering independently and end to end.
   - Run only the ablations needed to justify each existing component.

7. **Reliability, CI, and performance**
   - Add deterministic unit/integration/failure-mode tests and a fast ML smoke eval.
   - Make deployment depend on verification and correct the branch filter.
   - Run and save a clearly labeled local latency benchmark before optimizing.

8. **Evidence reports**
   - Generate machine-readable run directories, the evaluation report, README
     evidence sections, and resume evidence only from executed results.

## Phase 0 decision

Proceed without replacing the serving architecture. The first implementation
milestone should be the already-approved root UV dependency authority plus a narrow
MovieLens 32M download/environment bootstrap. It removes setup ambiguity and enables
the actual dataset and pipeline checks required by every later phase. No metric,
latency, reliability, production, or business-impact claim is currently supported.

## Legacy training code: historical audit record

The native/C++ training stack and the older duplicate Python training wrappers
were retained temporarily as reference material during this audit. They are
**not supported entry
points** for data transformation, model training, artifact creation, evaluation,
or deployment.

Do not run:

- `backend/scripts/run_full_pipeline.py`
- `backend/scripts/run_native_training.py`
- `backend/scripts/run_all_native.sh`
- `backend/scripts/run_mini_test.py`
- `backend/features/native/`
- `backend/training/retrieval/native/`
- `backend/training/ranking/native/`
- `backend/training/bin/`
- `backend/training/retrieval/train_als.py`
- `backend/training/retrieval/train_two_tower.py`
- `backend/training/retrieval/build_tfidf.py`
- `backend/training/retrieval/build_content.py`
- `backend/features/generate_training_features.py`
- `backend/scripts/finalize_artifacts.py`
- `backend/scripts/compress_content_model.py`

The replacement is now the Python-only pipeline built from the validated
TMDB-keyed Parquet datasets and temporal split contract. It has completed
deterministic fixture tests, artifact generation, full training/evaluation,
bundle validation, and serving smoke tests. The deletion recommendations in
this historical section are superseded; do not restore those paths.
