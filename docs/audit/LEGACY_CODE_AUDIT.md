# Legacy Code and Repository Rationalization Audit

**Audit date:** 2026-08-13  
**Repository:** `movie-recommendation-system`  
**Branch/worktree:** `chore/local-uv-bootstrap` (worktree contains an in-progress migration)  
**Initial audit mode:** read-only. Cleanup changes are recorded separately in
the post-cleanup section below.

> **Status note:** Sections below preserve the original forensic evidence. The
> current state after approved cleanup is recorded in **Post-cleanup
> verification** at the end of this document and supersedes historical counts
> and deletion recommendations.

## Executive audit

The repository is functional locally, but it currently contains two competing systems:

1. The new, content-addressed Python pipeline: `backend/data_pipeline/` → `backend/training/` → `backend/serving/` → an immutable four-retriever/ranker bundle.
2. The historical S3/DynamoDB/native pipeline: `backend/pipeline/`, `backend/retrieval/`, `backend/ranking/inference/`, `backend/features/native/`, `backend/training/*/native/`, and the old `backend/scripts/*` orchestration.

The new path is evidenced by successful preparation, temporal splitting, validation, retrieval training (ALS, item graph, two-tower, content), ranking training, test evaluation, bundle creation, local API smoke testing, and a warm benchmark with zero HTTP/model errors. The old path is not harmless historical text: it is still imported by the lifecycle fallback, referenced by the Docker/SAM deployment, and referenced by legacy scripts. It therefore cannot be deleted by filename inspection alone.

### Health assessment

* **Local model path:** healthy and reproducible when `MODEL_BUNDLE_DIR` points to a validated bundle.
* **Local fallback path:** legacy and materially different (S3-backed retrievers, old feature names, old ranker artifact names).
* **Lambda deployment path:** currently inconsistent with the new bundle path. `backend/Dockerfile.lambda` does not copy `serving/` or the model bundle, while `backend/main.py` imports `serving` when the bundle path is configured. SAM/GitHub Actions still require an S3 artifact bucket.
* **Training path:** new CLIs are canonical; old Python wrappers and native binaries are still present and several are demonstrably broken or incompatible.
* **Documentation:** architecture docs are partly current, but evaluation and deployment documents still contain stale claims.
* **Repository hygiene:** large generated artifacts are ignored, but tracked native ELF binaries and a generated processed JSON metadata file remain in source control.

### Counts (defined audit scope)

The inventory covers all 224 tracked files, the untracked canonical migration files under `backend/data_pipeline/`, `backend/evaluation/`, `backend/serving/`, `backend/training/`, `backend/tests/`, and all meaningful runtime/training/deployment directories. Homogeneous generated/artifact folders are counted as groups rather than expanding millions of data rows.

* Files inspected: **224 tracked files**, plus **the untracked canonical migration files and generated artifacts present in the worktree**.
* Files/groups confirmed active: **13** canonical responsibility groups.
* Files/groups marked KEEP: **8**.
* Files/groups marked KEEP + DOCUMENT: **2**.
* Files/groups marked REFACTOR: **9**.
* Files/groups marked CONSOLIDATE: **6**.
* Files/groups marked DEPRECATE: **8**.
* Files/groups marked GENERATED / SHOULD NOT BE SOURCE: **3**.
* Files/groups safe to delete immediately: **0**. (Candidates below require the stated verification gate.)
* Files/groups UNKNOWN: **4**.
* Dead symbol candidates: **3** confirmed, plus **2** requiring consumer checks.
* Unused dependencies: **0** proven unused; **1** scope problem and **4** probable training-only scope candidates.
* Stale/duplicate configuration entries or files: **6** groups.
* Broken entrypoints or paths: **6**.
* Duplicate/competing implementations: **6** areas.

These are audit-scope counts, not a claim that every individual generated artifact has been manually enumerated.

## A. Canonical system map

### A.1 Current intended path

```text
raw MovieLens/TMDB-enriched inputs
        |
        v
backend/data_pipeline/cli.py
  prepare -> immutable dataset version
  split   -> temporal train/validation/test
  ranking-prepare -> ranking events/retrieval train
        |
        +--> backend/training/retrieval/cli.py
        |      ALS, item_graph, two_tower, tfidf/content
        |
        +--> backend/data_pipeline/cli.py ranking-candidates
        |      four retrievers, deduplication, source-rank scores
        |
        +--> backend/data_pipeline/cli.py ranking-features
        |      ranking-features-v1/v2 contract
        |
        +--> backend/training/ranking/cli.py
               LightGBM LambdaRank + validation/test metrics
                        |
                        v
backend/serving/model_bundle.py
  immutable bundle: four retrievers + ranker + feature schema + popularity state
                        |
                        v
backend/main.py -> api.v1 routers -> common.lifecycle
                        |
                        v
backend/serving/recommender.py / serving.pipeline.py
  retrieve -> RRF/fusion -> rank -> seed/dedup filtering -> TMDB metadata
```

### A.2 Entrypoint registry

| Entrypoint | Invocation/consumer | Inputs | Outputs | Status |
| --- | --- | --- | --- | --- |
| `backend/main.py:app`, `main.handler` | Uvicorn, Lambda handler, `docker-compose`/SAM | settings, API routes, optional bundle | HTTP API/Lambda response | **KEEP; active** |
| `backend/data_pipeline/cli.py` | `python -m data_pipeline.cli` | raw/enriched data, YAML configs | immutable data/ranking versions | **KEEP; canonical** |
| `backend/training/retrieval/cli.py` | `python -m training.retrieval.cli` | train parquet/catalog/config | four retriever artifacts | **KEEP; canonical** |
| `backend/training/ranking/cli.py` | `python -m training.ranking.cli` | ranking feature artifacts | LightGBM ranker artifact | **KEEP; canonical** |
| `backend/evaluation/cli.py` | `python -m evaluation.cli` | version/split/artifacts | metrics/evaluation manifests | **KEEP; canonical** |
| `backend/serving/model_bundle.py` | bundle build/load command | five model artifacts + train counts | immutable bundle | **KEEP; canonical** |
| `backend/serving/smoke.py`, `benchmark.py` | local release gate | running API, bundle, seed IDs | smoke/latency JSON | **KEEP; canonical** |
| `backend/api/main.py:app` | comment only (`uvicorn api.main:app`) | old `data_io`/`inference` imports | none | **P0 broken; do not run** |
| `backend/scripts/run_full_pipeline.py` | manual script | old configs/native scripts | old native artifacts | **DEPRECATE; competing** |
| `backend/scripts/run_native_training.py`, `run_all_native.sh` | manual/native workflows | old CSV/binary data | old native artifacts | **DEPRECATE; competing** |
| `backend/scripts/start_backend.sh` | `backend/Dockerfile`/compose | DynamoDB local and native search data | dev Uvicorn process | **KEEP temporarily; document as dev-only** |
| `.github/workflows/deploy.yml` + `template.yaml` | push to `main`/manual workflow | Lambda Dockerfile, S3 parameter | AWS image/SAM stack | **P0 inconsistent with bundle path** |

### A.3 Major-directory ownership

| Directory/group | Responsibility | Consumer | Classification | Action |
| --- | --- | --- | --- | --- |
| `backend/data_pipeline/` | immutable data, split, ranking-data construction | training/evaluation CLIs | KEEP | canonical data owner |
| `backend/training/retrieval/` (`cli.py`, `build_*.py`) | four retriever training/loading | data pipeline, bundle builder | KEEP | canonical training owner |
| `backend/training/ranking/` (`cli.py`, `pipeline.py`, `features.py`) | ranking training/evaluation | feature artifacts, bundle builder | KEEP | canonical ranking owner |
| `backend/evaluation/` | baselines, metrics, runners | CLI/tests | KEEP | canonical evaluation owner |
| `backend/serving/` | compact artifact loading and four-source serving | lifecycle/API | KEEP | canonical serving owner |
| `backend/main.py`, `backend/api/v1/` | FastAPI/Lambda boundary | Uvicorn/SAM/frontend | KEEP | active API boundary |
| `backend/common/clients/`, `MovieStore` | TMDB/IMDb metadata clients | API/serving | KEEP + DOCUMENT | clarify live metadata fallback |
| `backend/pipeline/`, `backend/features/builder.py`, `backend/retrieval/inference/`, `backend/ranking/inference/` | old fallback recommendation path | `common.lifecycle` when bundle unset | REFACTOR/DEPRECATE | migrate or remove fallback |
| `backend/training/*/native/`, `backend/features/native/` | C++/binary historical pipeline | old scripts/Makefiles | DEPRECATE | retain until clean-room migration gate |
| `backend/scripts/` | mixed data enrichment, native orchestration, verification, upload | manual commands and Docker start | DEPRECATE/CONSOLIDATE | split supported scripts from legacy |
| `backend/configs/*.yml` | old system/ranker/features/S3 config | legacy runtime/scripts | CONSOLIDATE | migrate consumers to YAML contracts |
| `backend/configs/*.yaml` | new data/eval/training config | canonical CLIs | KEEP | document ownership |
| `frontend/` | UI and API client | browser users | KEEP | outside ML cleanup except API contract checks |
| `backend/data/versions/`, `backend/artifacts/`, `backend/model_bundle/` | generated datasets/models/releases | local training/serving | GENERATED / SHOULD NOT BE SOURCE | keep ignored; publish release bundle separately |

## B. Runtime reachability

### B.1 Active runtime graph

`backend/main.py` imports the API routers, `common.lifecycle`, logging/background tasks, and `Mangum`. With `MODEL_BUNDLE_DIR` set, `common.lifecycle.get_pipeline()` constructs `MovieStore`, loads `BundleRecommender`, and returns `BundleRecommendationPipeline`. The local smoke command and 50-request warm benchmark completed with zero model/HTTP errors and five seed metadata records.

### B.2 Competing runtime graph

When `MODEL_BUNDLE_DIR` is empty, the same lifecycle module imports and constructs `FeatureBuilder`, `RecallService`, `LGBMRanker`, and the old `RecommendationPipeline`. Those classes load S3 artifacts through `S3ArtifactRepository`, use the old `feat_*` feature contract, and use old artifact keys from `configs/system.yml`. This is a live fallback, not dead text. It is a separate runtime architecture and a parity risk.

### B.3 Broken runtime path

`backend/api/main.py` is a second FastAPI application. Its import graph references `data_io.data_loader` and `inference.pipeline`, neither of which exists in the repository. Verified command:

```text
UV_CACHE_DIR=/tmp/movie-recs-uv-cache PYTHONPATH=backend \
  uv run --frozen python -c 'import api.main'
-> ModuleNotFoundError: No module named 'data_io'
```

The only in-repository execution hint is a comment at `backend/api/main.py:154`. Classification: **P0 / DEPRECATE, conditional DELETE after command/documentation search**.

## C. Training reachability and artifact matrix

| Model/index | Canonical training implementation | Output artifact | Canonical serving loader | Compatible? | Status |
| --- | --- | --- | --- | --- | --- |
| ALS | `training.retrieval.cli als` → `build_als.py` | `faiss.index`, `item_embeddings.npy`, `tmdb_id_to_idx.json`, `manifest.json` | `serving.model_bundle` compact vector retriever | Yes; verified in bundle | KEEP |
| Item graph | `training.retrieval.cli item_graph` → `build_item_graph.py` | `neighbor_positions.npy`, `tmdb_id_to_idx.npy`, `manifest.json` | `serving.model_bundle` graph loader | Yes; verified in bundle | KEEP |
| Two-tower | `training.retrieval.cli two_tower` → `build_two_tower.py` | FAISS/index/embedding/ID map/manifest | `serving.model_bundle` compact vector retriever | Yes; verified in bundle | KEEP |
| TF-IDF | `training.retrieval.cli tfidf` → `build_content_retriever.py` | vectorizer/SVD/embedding/FAISS/ID map/manifest | `serving.model_bundle` content-compatible loader | Yes; verified by artifact loader | KEEP |
| Content | `training.retrieval.cli content` → same `build_content_retriever.py` implementation with field weights | same content artifact family, manifest `model_type=content` | `serving.recommender` reads content fields/weights | Yes; full bundle built | KEEP |
| LightGBM ranker | `training.ranking.cli` → `training/ranking/pipeline.py` | `model.txt`, feature schema, popularity counts, manifest | `serving.recommender` | Yes; validation/test and bundle load verified | KEEP |
| Old ALS/TF-IDF/content/two-tower | `retrieval/models/*.py` + old S3 keys | old mutable S3 artifacts under `configs/system.yml` | `retrieval.inference.recall` | Separate contract; not bundle-compatible | DEPRECATE/CONSOLIDATE |
| Old ranker | `training/ranking/train_ranker*.py`, `train_from_csv.py` | old `lgbm_lambdarank.txt`, `feat_*` data | `ranking/inference/lgbm.py` | Separate feature/artifact contract | DEPRECATE/CONSOLIDATE |
| Native retrievers/ranker | C++ `backend/training/*/native` + scripts | `.bin`, text maps, native rank files | `finalize_artifacts.py`/old S3 upload | Not the bundle contract | DEPRECATE |

### C.1 Artifact correctness finding

The new bundle builder validates component manifests, dataset versions, ID schema, feature schema, and payload hashes. The old upload/finalize path writes different names and fixed S3 keys and is not consumed by the new loader. This is a migration boundary that must be explicit before removing either side.

## D. Findings

Each finding includes location, evidence, current role, risk, recommendation, replacement, and verification. No action below was applied during this audit.

### LEGACY-001 — P0 — BROKEN — `backend/api/main.py`

* **Classification:** DEPRECATE; DELETE only after the verification gate.
* **Evidence:** import fails with `ModuleNotFoundError: data_io`; its `inference.pipeline` dependency is also absent. No workflow, Dockerfile, or active module imports it; only a stale `uvicorn api.main:app` comment exists.
* **Current role:** duplicate FastAPI app from the historical architecture.
* **Problem:** a supported-looking entrypoint cannot execute and confuses API ownership.
* **Recommendation:** mark unsupported immediately in docs; then remove the file and any stale references once repository-wide CLI/documentation search is clean.
* **Replacement:** `backend/main.py:app` / `main.handler`.
* **Risk:** Medium until all external/manual usage is ruled out; Low afterward.
* **Verification:** `rg -n 'api\.main|uvicorn api\.main' .`; import `main`; API smoke test; full pytest.

### LEGACY-002 — P0 — REFACTOR — `backend/Dockerfile.lambda`, `template.yaml`, `.github/workflows/deploy.yml`

* **Evidence:** Lambda image copies `api`, `common`, `configs`, `features`, `logger`, `pipeline`, `ranking`, `retrieval`, but not `serving/` or `model_bundle/`. Active `main.py`/lifecycle imports `serving` for the new path. SAM requires `S3BucketName`, injects `S3_ARTIFACT_BUCKET`, and grants `S3ReadPolicy`; deploy workflow passes the bucket.
* **Current role:** AWS deployment path for the old image/runtime contract.
* **Problem:** the deployed image cannot reproduce the validated local bundle path, and the deployment contract still assumes runtime S3 artifacts.
* **Recommendation:** choose and document one production contract: bake a validated bundle into the image, or deliberately retain S3. For the current design, package `serving/` and the release bundle and remove obsolete runtime S3 requirements only after deployment validation.
* **Replacement:** bundle-backed `main.handler`.
* **Risk:** High; deployment-critical.
* **Verification:** build Lambda image, run container import/startup, invoke `/ping` and `/api/v1/recommendations`, validate SAM, run smoke against the image.

### LEGACY-003 — P0 — REFACTOR — `backend/logger/services/mlflow_logger.py`

* **Evidence:** module-level code calls `mlflow.set_tracking_uri()` and `get_or_create_experiment()` during import. Importing `backend/main.py` without `MLFLOW_ALLOW_FILE_STORE=true` failed under a local file-backed MLflow configuration with MLflow's file-store maintenance error. `backend/Dockerfile.lambda` sets `ENVIRONMENT=PROD` but does not set a valid remote MLflow URI or allow the file store.
* **Current role:** online inference metrics and sampled traces.
* **Problem:** optional observability prevents application startup and hard-codes old model version names (`lgbm_v1`, `als_v1`, `two_tower_v1`, `faiss_items_v1`).
* **Recommendation:** make telemetry lazy and fail-open or use an explicit production tracking contract; source model lineage from the loaded bundle manifest.
* **Replacement:** a runtime-safe logger initialized from the active bundle/environment.
* **Risk:** High; startup and monitoring behavior.
* **Verification:** import/startup with no MLflow service, with local file store, and with the configured production URI; recommendation smoke; flush test.

### LEGACY-004 — P0 — BROKEN — old trainer wrappers

* **Locations:** `backend/training/retrieval/train_als.py`, `train_two_tower.py`, `build_content.py`.
* **Evidence:** imports fail under the project environment: `ALSBuilder`, `TwoTowerBuilder`, and `ContentBasedBuilder` cannot be imported from the current model modules. The canonical CLI uses `build_als.py`, `build_two_tower.py`, and `build_content_retriever.py` instead.
* **Current role:** historical Python wrappers around the former retrieval builders.
* **Problem:** commands appear to exist but cannot train artifacts.
* **Recommendation:** deprecate/document the wrappers, then remove them after checking external/manual usage. Do not add compatibility builder classes merely to preserve this path.
* **Replacement:** `python -m training.retrieval.cli {als,two_tower,content}`.
* **Risk:** Low for the current system; Medium for unknown external users.
* **Verification:** repository-wide reference search, README/CI/script search, canonical CLI smoke training.

### LEGACY-005 — P1 — CONSOLIDATE — old S3 retrievers/ranker vs bundle retrievers/ranker

* **Locations:** `backend/retrieval/models/*.py`, `backend/retrieval/inference/recall.py`, `backend/ranking/inference/lgbm.py`, `backend/serving/*.py`.
* **Evidence:** lifecycle imports both stacks. Old classes use `S3ArtifactRepository` and `configs/system.yml`; bundle classes load content-addressed payloads and validate `ranking-features-v2` contracts. Their artifact names, feature names, and fusion paths differ.
* **Current role:** old fallback runtime plus new production candidate.
* **Problem:** two sources of truth can return different recommendations and metrics depending only on one environment variable.
* **Recommendation:** make bundle-backed serving the sole supported path, keep old code behind an explicitly named migration/deprecation boundary, migrate any required consumers, then remove old loaders and keys.
* **Replacement:** `serving.recommender.BundleRecommender` and `serving.pipeline.BundleRecommendationPipeline`.
* **Risk:** High until deployment and fallback consumers are verified; Low afterward.
* **Verification:** bundle/API contract tests, old-path consumer inventory, image smoke, no-S3 local startup.

### LEGACY-006 — P1 — CONSOLIDATE — old data/features/ranking pipelines

* **Locations:** `backend/data/builder.py`, `backend/features/builder.py`, `backend/features/generate_training_features.py`, `backend/training/ranking/train_ranker.py`, `train_ranker_v2.py`, `train_from_csv.py`.
* **Evidence:** canonical `data_pipeline.ranking` creates temporal, content-addressed ranking data and canonical `training.ranking` consumes `ranking-features-v1/v2`. Old scripts use `ranking_dataset.parquet`, `ranking_featured.parquet`, `feat_*` fields, random/group splits, or native `rank.train` files.
* **Current role:** historical ranking experiments and fallback training paths.
* **Problem:** duplicated labels/features/splits create leakage and artifact-parity risk.
* **Recommendation:** declare the temporal pipeline canonical; preserve only a clearly named baseline if it is still intentionally evaluated. Migrate useful utilities, then remove duplicate trainers.
* **Replacement:** `backend/data_pipeline/ranking.py` and `backend/training/ranking/{features,pipeline,cli}.py`.
* **Risk:** Medium/High because experiments may be referenced externally.
* **Verification:** regenerate ranking train/validation/test, compare contracts, train ranker, final test evaluation.

### LEGACY-007 — P1 — DEPRECATE — native/C++ training and feature pipeline

* **Locations:** `backend/features/native/`, `backend/training/retrieval/native/`, `backend/training/ranking/native/`, `backend/training/Makefile`, `backend/scripts/run_native_training.py`, `run_all_native.sh`, `prepare_data.py`.
* **Evidence:** scripts compile/run native binaries, produce `.bin`/text-map artifacts, and feed `finalize_artifacts.py`/S3 upload. The current release was trained by Python CLIs and loaded by the bundle; no active canonical command consumes native outputs. Several compiled ELF binaries are tracked alongside their source.
* **Current role:** historical performance experiment and old end-to-end training path.
* **Problem:** it creates a second artifact contract and requires native toolchains not present in the Lambda runtime.
* **Recommendation:** retain source only while measuring whether native performance is still needed; stop treating it as supported; remove tracked binaries first after a reproducibility/build gate, then retire source/scripts in a separate change.
* **Replacement:** Python retrieval/ranking CLIs with progress and immutable manifests.
* **Risk:** Medium; high only if an external job still invokes it.
* **Verification:** clean checkout native build (if retaining), compare artifact quality/latency, search CI/manual docs, canonical Python end-to-end run.

### LEGACY-008 — P1 — REFACTOR — `backend/common/lifecycle.py`

* **Evidence:** imports both legacy and bundle stacks at module import; chooses architecture based on `MODEL_BUNDLE_DIR` and returns a legacy-typed annotation for both.
* **Current role:** global lazy singleton for store and pipeline.
* **Problem:** production selection is implicit, imports unnecessary dependencies, and fallback behavior is undocumented.
* **Recommendation:** make the bundle path explicit and fail closed when production requires it; isolate a separately named legacy adapter during migration.
* **Replacement:** one bundle-backed lifecycle contract.
* **Risk:** High until fallback users are inventoried.
* **Verification:** unit lifecycle tests for bundle, explicit legacy mode, missing bundle, and production startup.

### LEGACY-009 — P1 — REFACTOR — bundle/deployment release contract

* **Locations:** `backend/serving/model_bundle.py`, `backend/model_bundle/` (ignored generated release), Docker/SAM files.
* **Evidence:** bundle builder/loaders enforce hashes, dataset version, TMDB ID schema, and ranker feature schema. The physical bundle is ignored and not copied by `Dockerfile.lambda`; Docker/SAM have no release manifest or bundle-presence gate.
* **Current role:** local immutable release artifact.
* **Problem:** a locally validated model set is not guaranteed to be the artifact shipped to production.
* **Recommendation:** define a release directory/manifest contract and add a build-time presence/hash gate. Keep model payloads out of Git, but make the image build consume a declared release input.
* **Replacement:** validated `model_bundle-v1` release package.
* **Risk:** High; deployment correctness.
* **Verification:** clean checkout release build, hash verification, image inspection, bundle load, API smoke.

### LEGACY-010 — P1 — REFACTOR — CI workflow lacks quality/release gates

* **Location:** `.github/workflows/deploy.yml`.
* **Evidence:** workflow builds/pushes/deploys only; it does not run pytest, Ruff, data/config validation, bundle validation, Docker startup, or serving smoke before deploy.
* **Current role:** deployment automation.
* **Problem:** broken imports, missing `serving/`, and incompatible bundle packaging can reach production.
* **Recommendation:** add minimal pre-deploy gates after the canonical contract is settled; do not add broad expensive full-data training to CI.
* **Replacement:** small deterministic unit/integration/release smoke gates.
* **Risk:** Medium.
* **Verification:** run workflow-equivalent commands locally and in a branch CI job.

### LEGACY-011 — P1 — REFACTOR — movie metadata fallback contract

* **Location:** `backend/api/v1/movies.py`, `backend/common/services/movie_store.py`.
* **Evidence:** route documentation says local DB → TMDB → IMDb, and calls `movie_store.tmdb_client`/`imdb_client`; current `MovieStore` is TMDB-backed and does not expose `imdb_client`. The route also documents an internal MovieLens ID while `MovieStore.get()` treats the value as TMDB ID.
* **Current role:** movie lookup/search endpoint.
* **Problem:** documented fallback and actual object contract disagree; missing metadata can fail at runtime.
* **Recommendation:** choose one explicit metadata contract (bundle/catalog first, then TMDB, optional IMDb) and type it at the store boundary.
* **Replacement:** one `MovieStore` resolver contract used by all routes.
* **Risk:** Medium.
* **Verification:** route tests for catalog hit, TMDB miss, new movie, missing poster/overview, and invalid ID semantics.

### LEGACY-012 — P2 — CONSOLIDATE — configuration sources

* **Locations:** `backend/configs/system.yml`, `features.yml`, `ranker.yml`, `settings.py`, new `*.yaml` files.
* **Evidence:** old YAML stores S3 keys, native paths, old feature names, and `content_based`/`tfidf` registry entries; new CLIs default to `data_pipeline.yaml`, `retrieval_training.yaml`, `ranking_training.yaml`, and `ranking_features.yaml`. `common.config` still loads the old YAML family for fallback runtime.
* **Current role:** two generations of config ownership.
* **Problem:** changing a value in one file may not affect the active command; stale paths are easy to select accidentally.
* **Recommendation:** publish a config ownership table, migrate remaining consumers, remove only after reference checks.
* **Replacement:** typed canonical YAML/Settings boundaries.
* **Risk:** Medium.
* **Verification:** config-load tests, `rg` consumer map, clean CLIs with explicit defaults.

### LEGACY-013 — P2 — GENERATED / SHOULD NOT BE SOURCE — tracked processed metadata

* **Location:** `backend/data/processed/movies_enriched.json`.
* **Evidence:** tracked JSON is a generated metadata summary (`schema_version`, row count, merge date, compression) and has no code references found by `rg`. It is distinct from ignored generated parquet/data-version outputs.
* **Current role:** likely historical merge metadata.
* **Problem:** generated, date-specific state in source control can drift from reproducible data manifests.
* **Recommendation:** verify no external fixture/manual workflow needs it; remove from source control and rely on `manifest.json`/versioned generation outputs. Do not delete during this audit.
* **Replacement:** immutable data-version manifest.
* **Risk:** Low after consumer check.
* **Verification:** `rg -n 'movies_enriched\.json' .`, data prepare/validate, tests.

### LEGACY-014 — P2 — GENERATED / SHOULD NOT BE SOURCE — tracked native ELF binaries

* **Locations:** `backend/features/native/{processor,sequence_builder,content_vectorizer,interaction_matrix_builder,ranker_feature_gen}`, `backend/training/retrieval/native/train_*`, `backend/training/ranking/native/converter`.
* **Evidence:** `file` reports ELF x86-64 executables tracked next to C/C++ source; Makefiles can rebuild them. They are not used by the canonical Python bundle path.
* **Current role:** checked-in build outputs for the native experiment.
* **Problem:** architecture-specific binaries are not reproducible source and inflate/confuse deployment and review.
* **Recommendation:** remove binaries from version control only after a clean native build/reproducibility decision; add ignore rules in the cleanup phase.
* **Replacement:** source + build command if native is retained; otherwise Python CLIs.
* **Risk:** Medium until external native usage is ruled out.
* **Verification:** clean native build, native smoke (if retained), canonical Python smoke.

### LEGACY-015 — P2 — DEPENDENCY SCOPE — `pyproject.toml`

* **Evidence:** all declared runtime packages have imports or command/config consumers somewhere; therefore no dependency is proven unused. However, `torch`, `implicit`, `scipy`, pandas, PyArrow, and scikit-learn are primarily training/data dependencies while the Lambda image installs the entire dependency set. `uvicorn`/pytest/Ruff are command/dev dependencies rather than application imports.
* **Current role:** single dependency environment for local, training, test, and Lambda paths.
* **Problem:** large cold-start/image surface and unnecessary native libraries in serving deployment.
* **Recommendation:** do not remove packages from the shared lockfile blindly. Split serving/training/dev dependency scopes or build a serving-only image after import tracing.
* **Replacement:** explicit runtime/ML-training/dev groups and a tested serving image.
* **Risk:** Medium.
* **Verification:** import manifest for serving, image size/startup benchmark, all training/test commands.

### LEGACY-016 — P2 — DEPRECATE — mutable legacy scripts

* **Locations:** `backend/scripts/finalize_metadata.py`, `prepare_data.py`, `run_mini_test.py`, `upload_artifacts.py`, `compress_content_model.py`, `verify_models.py`, `run_tests.py`.
* **Evidence:** scripts mutate fixed paths, rewrite `system.yml` (`run_mini_test.py`), use old artifact names/S3 keys, delete artifact directories, or validate native outputs. Canonical commands now write immutable content-addressed outputs.
* **Current role:** historical maintenance/manual workflow.
* **Problem:** commands can overwrite state and validate a different artifact contract from serving.
* **Recommendation:** label unsupported; replace useful checks with canonical validation/smoke commands; delete scripts only after usage inventory.
* **Replacement:** `data_pipeline.cli`, `evaluation.cli`, `serving.model_bundle`, `serving.smoke`, `serving.benchmark`.
* **Risk:** Medium.
* **Verification:** reference search, README/docs update, canonical command equivalents.

### LEGACY-017 — P2 — CONSOLIDATE — duplicate API schemas

* **Locations:** `backend/api/schemas/movie.py`, `backend/api/schemas/recommend.py`.
* **Evidence:** both define movie response shapes; `recommend.py` contains a duplicate `tmdbId` declaration. Active recommendation routes use `recommend.py`; `movie.py` has no active route import found.
* **Current role:** overlapping response contracts.
* **Problem:** clients can receive subtly different naming/alias behavior.
* **Recommendation:** identify frontend/OpenAPI consumers, choose one canonical DTO, retain a compatibility alias only if required.
* **Replacement:** one API schema module per public contract.
* **Risk:** Medium.
* **Verification:** OpenAPI snapshot, frontend type/API tests, route tests.

### LEGACY-018 — P3 — KEEP + DOCUMENT — frontend and supported metadata clients

* **Locations:** `frontend/`, `backend/common/clients/`, `backend/common/services/tmdb_catalog_service.py`.
* **Evidence:** frontend calls the active API; TMDB/IMDb clients are used by metadata routes/enrichment or are required for new-movie cold start. Their presence is justified even when retrieval artifacts are local.
* **Current role:** user-facing selection, metadata enrichment, and cold-start metadata.
* **Problem:** ownership and live-vs-offline use are not always obvious.
* **Recommendation:** document that metadata APIs are not model retrieval and define failure/cache behavior; do not remove.
* **Replacement:** none.
* **Risk:** Low.
* **Verification:** frontend/API smoke and metadata fallback tests.

## E. Dead symbol candidates

These are symbol-level candidates inside files that otherwise remain in the repository:

| Symbol | Location | Evidence | Classification |
| --- | --- | --- | --- |
| `generate_features()` path using `FeatureBuilder.from_paths` | `backend/features/generate_training_features.py:32-33` | current `FeatureBuilder` has no `from_paths` method; old input/output paths are not canonical | DELETE or REFACTOR after consumer check |
| import-time `ONLINE_EXP_ID` setup | `backend/logger/services/mlflow_logger.py:30-33` | side effect occurs before any request and breaks startup in some environments | REFACTOR, not delete the logging API |
| `movie_store.imdb_client`/`tmdb_client` route assumptions | `backend/api/v1/movies.py:55,75` | current store contract does not expose both attributes | REFACTOR route/store boundary |
| old builder imports (`ALSBuilder`, `TwoTowerBuilder`, `ContentBasedBuilder`) | old trainer wrappers | import execution fails; canonical builders are different symbols | DELETE wrappers after usage gate |
| old `feat_*` feature fallback/zero-fill | `backend/ranking/inference/lgbm.py` | only legacy ranker path consumes it; not bundle feature contract | DELETE after fallback migration |

## F. Duplicate / competing implementations

| Responsibility | Implementation A | Implementation B | Canonical candidate | Rationale |
| --- | --- | --- | --- | --- |
| Runtime pipeline | `pipeline.pipeline.RecommendationPipeline` | `serving.pipeline.BundleRecommendationPipeline` | bundle pipeline | only bundle path matches validated release artifacts |
| Retrieval loaders | `retrieval.models.*` + S3 | `training/retrieval/build_*` + compact bundle | bundle loaders | one artifact/hash/ID contract |
| Retrieval training | native C++ + old wrappers | `training.retrieval.cli` | Python CLI for now | current reproducible runs and tests; retain native only if benchmark justifies |
| Ranking training | `train_ranker*.py`/native converter | `training.ranking.cli` | temporal canonical CLI | leakage-safe, content-addressed features and test protocol |
| Feature generation | `features.builder`/`generate_training_features.py` | `data_pipeline/ranking.py` + `training/ranking/features.py` | new feature contract | training/serving parity is explicit |
| Configuration | `system.yml`/`features.yml`/`ranker.yml` | typed/new `*.yaml` + Settings | new configs plus minimal Settings | old files encode S3/native assumptions |

## G. Broken or unexecutable paths

1. `api.main` import fails because `data_io` is absent.
2. Old retrieval trainer wrappers import missing builder symbols.
3. `features.generate_training_features.generate_features()` calls missing `FeatureBuilder.from_paths` and old paths.
4. Lambda image omits `serving/` while active bundle runtime imports it.
5. Lambda/SAM deployment has no validated bundle packaging contract and still requires runtime S3 configuration.
6. Import-time MLflow setup can fail application startup when the file-store flag/remote tracking URI is absent.

Broken does not mean dead: each path is classified above with a migration/deletion gate.

## H. Dependency cleanup

| Dependency | Current evidence | Scope recommendation |
| --- | --- | --- |
| `aiohttp` | TMDB/IMDb clients | serving + enrichment |
| `boto3` | S3/DynamoDB repositories and legacy scripts/template | serving only if legacy storage remains; otherwise training/deploy tooling |
| `faiss-cpu`, `lightgbm`, `joblib`, `numpy` | bundle loading/ranking | required serving |
| `implicit`, `torch` | ALS/two-tower training | training only; verify no serving import |
| `pandas`, `pyarrow`, `scipy`, `scikit-learn` | data pipeline, content/ranking training, serialization | training/data; assess serving transitive imports before splitting |
| `mlflow` | training tracking and online logger | training/optional monitoring; make serving optional |
| `uvicorn`, `pytest`, `pytest-asyncio`, `ruff` | commands/tests | dev/deployment tooling, not runtime |

No package is marked “remove” from static evidence alone. The concrete next action is dependency-scope separation plus image import testing.

## I. Configuration and environment audit

### I.1 Configuration ownership

| Config | Current consumer | Status |
| --- | --- | --- |
| `configs/data_pipeline.yaml` | data pipeline CLI | KEEP |
| `configs/evaluation.yaml` | evaluation CLI | KEEP |
| `configs/retrieval_training.yaml` | retrieval CLI | KEEP |
| `configs/ranking_data.yaml` | ranking-data CLI | KEEP |
| `configs/ranking_features.yaml` | feature generation/ranker | KEEP |
| `configs/ranking_training.yaml` | ranker CLI | KEEP |
| `configs/mlflow.yaml` | tracking/config tests | KEEP + DOCUMENT |
| `configs/system.yml` | legacy runtime/scripts | CONSOLIDATE/DEPRECATE |
| `configs/features.yml`, `ranker.yml` | legacy feature/ranker path | CONSOLIDATE/DEPRECATE |
| `configs/settings.py` | API/runtime and environment | REFACTOR boundary; retain until migration complete |

### I.2 Environment variables

Important variables found in code/deployment include `MODEL_BUNDLE_DIR`, `ENVIRONMENT`, `MLFLOW_TRACKING_URI`, `MLFLOW_ALLOW_FILE_STORE`, `S3_ARTIFACT_BUCKET`, `TMDB_ACCESS_TOKEN`, `IMDB_API_KEY`, `ALLOWED_ORIGINS`, `DYNAMODB_*`, `NEXT_PUBLIC_API_BASE`, and `LOG_FORMAT_JSON`. The first group is active in the bundle/local path; S3/DynamoDB variables remain for legacy fallback/deployment. The audit found no secret values and does not reproduce them.

Required follow-up: generate a consumer/default/required table and remove only variables whose last consumer is removed.

## J. Documentation drift

* `docs/evaluation/EVALUATION_REPORT.md` still says ALS/TF-IDF/content/two-tower/ranker are not measured, while artifacts and user-run outputs show full validation/test runs.
* `docs/architecture/MODEL_BUNDLE.md` contains an “incomplete until content-aware ranking-features-v2” release statement that is stale after the successful content bundle and ranking runs.
* `backend/README.md` and root README still describe `configs/system.yml`, the old `RecommendationPipeline`, and S3-oriented model paths without clearly labeling them as legacy.
* `docs/audit/PROJECT_AUDIT.md` is a useful historical audit but its “candidate/unverified” language predates the now-validated Python/bundle path; it should be superseded, not silently treated as current truth.
* `backend/api/v1/movies.py` documents a local DB → TMDB → IMDb fallback not implemented by the current `MovieStore` contract.
* `backend/scripts/start_backend.sh` and backend README use `--reload` in a container command; this is a development path, not production behavior.

## K. Proposed canonical architecture

```text
backend/configs/{data_pipeline,evaluation,retrieval_training,ranking_data,
                ranking_features,ranking_training,mlflow}.yaml
        |
backend/data_pipeline/                  # immutable datasets and ranking data
        |
backend/training/retrieval/cli.py       # ALS, item_graph, two_tower, tfidf/content
        |
backend/data_pipeline/ranking.py        # candidate generation and source scores
        |
backend/training/ranking/{features,pipeline,cli}.py
        |
backend/serving/model_bundle.py         # immutable release assembly/verification
        |
backend/main.py + api.v1 + common.lifecycle
        |
backend/serving/{recommender,pipeline}.py
        |
TMDB/IMDb metadata boundary + FastAPI/Lambda response
```

One canonical implementation should own each responsibility:

* data versions: `backend/data_pipeline/`;
* retrieval training: `backend/training/retrieval/`;
* ranking training: `backend/training/ranking/`;
* evaluation: `backend/evaluation/`;
* bundle and inference: `backend/serving/`;
* API boundary: `backend/main.py` + `backend/api/`;
* production release: Docker/SAM consuming a declared immutable bundle.

The old S3/native path should be an explicitly isolated migration target, not an implicit fallback.

## L. Target repository structure

Do not move files as part of this audit. The lowest-risk target is a responsibility cleanup, not a mass rename:

```text
backend/
  api/                 # public HTTP/Lambda routes and schemas
  common/              # clients, typed models, shared settings
  configs/              # one documented owner per config family
  data_pipeline/       # immutable data/ranking construction
  evaluation/          # metrics, baselines, runners
  serving/             # bundle loading and inference
  training/
    retrieval/         # canonical retriever trainers
    ranking/           # canonical ranker trainer
  scripts/              # only supported wrappers; legacy isolated/removed
  tests/                # unit/integration/release smoke
frontend/
docs/
  architecture/
  evaluation/
  audit/
```

Keep `retrieval/`, `ranking/`, `pipeline/`, and native directories untouched until their consumers are migrated; moving them first would hide the actual dependency problem.

## M. Safe deletion candidates (gated, not executed)

There are no unconditional deletions at audit time. The following are the safest candidates once the listed gate passes:

| Candidate | Evidence | Replacement | Risk | Gate |
| --- | --- | --- | --- | --- |
| `backend/data/processed/movies_enriched.json` | generated JSON metadata, no repository refs found | data-version `manifest.json` | Low | external/manual consumer search, data prepare/validate, tests |
| tracked native ELF binaries listed in LEGACY-014 | build outputs, source/Makefile exists | clean build outputs or Python CLIs | Medium | clean native build decision and external usage search |
| old trainer wrappers in LEGACY-004 | imports demonstrably fail | canonical retrieval CLI | Medium | docs/CI/manual command search |
| `backend/api/main.py` | import demonstrably fails | `backend/main.py` | Medium | command/docs/deployment search |

These are recommendations for a later cleanup phase, not changes made now.

## N. Refactoring candidates by concern

### Training/data

1. Make `data_pipeline` and `training` the only supported commands; add a small compatibility/deprecation notice for old scripts.
2. Remove or isolate `features/generate_training_features.py` after migrating any remaining consumer.
3. Keep one feature schema shared by candidate generation, ranking training, bundle validation, and serving.

### Retrieval/ranking

1. Isolate old S3 retrievers behind a legacy package or remove them after deployment migration.
2. Do not merge algorithm implementations that have different artifact contracts; consolidate loaders at the bundle boundary.
3. Keep content/TF-IDF algorithm diversity, but share the single field-weighted trainer already used by `build_content_retriever.py`.

### API/serving

1. Make bundle presence and dataset/schema checks mandatory for production.
2. Fix the MovieStore/route metadata contract before claiming IMDb fallback support.
3. Replace import-time MLflow setup with optional/lazy telemetry.

### Deployment

1. Decide bundle-in-image vs S3; the current local architecture implies bundle-in-image.
2. Package `serving/` and the declared bundle into the Lambda image and add a release manifest gate.
3. Add image startup/smoke checks before SAM deployment.

### Configuration/docs

1. Publish config ownership and environment-variable tables.
2. Update evaluation and bundle docs from “planned/unmeasured” to verified artifact/result references.
3. Label native/S3 scripts as unsupported until removed.

## O. Cleanup execution order

### Stage 0 — Contracts and evidence

1. Freeze the canonical bundle/data/ranking schemas.
2. Write a deployment release contract and config ownership table.
3. Add reference searches/import checks without deleting code.

**Gate:** all current local smoke, benchmark, training smoke, and bundle validation commands pass.

### Stage 1 — Generated/source-control hygiene

1. Remove generated JSON metadata and tracked native binaries only after their gates.
2. Keep generated datasets/models ignored; publish immutable release bundles outside source control.

**Gate:** clean checkout can reproduce required fixtures/artifact manifests.

### Stage 2 — Broken entrypoints

1. Deprecate/remove `api.main` and old trainer wrappers.
2. Remove stale command/documentation references.

**Gate:** import checks, CLI help checks, full tests, API smoke.

### Stage 3 — Runtime consolidation

1. Migrate production/deployment to bundle-only serving.
2. Remove lifecycle fallback and old S3 retrievers/ranker after deployment verification.

**Gate:** image/SAM start, bundle load, recommendation smoke, latency benchmark, no runtime S3 dependency if that is the chosen contract.

### Stage 4 — Training/dependency cleanup

1. Retire old ranking/data/native orchestration scripts after reference search.
2. Split serving/training/dev dependencies and rebuild the image.

**Gate:** canonical end-to-end data → training → bundle → serving run and all tests.

### Stage 5 — Documentation and naming

1. Update README/architecture/evaluation docs.
2. Rename only modules whose ownership remains misleading after consolidation.

**Gate:** every supported command in docs executes from a clean checkout or is explicitly marked historical.

## P. Verification plan

Run each batch with the smallest relevant checks:

```text
ruff check backend frontend (where applicable)
uv run --frozen pytest backend/tests/unit
uv run --frozen pytest backend/tests/integration
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli prepare
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli split --dataset-version <version>
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli validate --dataset-version <version>
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli <model> --ci
PYTHONPATH=backend uv run --frozen python -m training.ranking.cli --...  # deterministic small fixture in CI
PYTHONPATH=backend uv run --frozen python -m serving.model_bundle --... 
PYTHONPATH=backend uv run --frozen python -m serving.smoke --base-url <url> --seed-tmdb-ids ...
PYTHONPATH=backend uv run --frozen python -m serving.benchmark --bundle-dir <dir> --base-url <url> ...
docker build -f backend/Dockerfile.lambda .
sam validate --template-file template.yaml
```

For deletion/refactor batches, also run `git grep`/`rg` for removed paths, import every supported module, and inspect the bundle manifest hashes. Do not run full-data training in CI; use deterministic fixtures and reserve full-data runs for release jobs.

## Q. Do not touch yet

| Component | Why suspicious | Missing evidence | Next investigation |
| --- | --- | --- | --- |
| `backend/features/native/` C++ sources | old and not used by current bundle | whether native is still a performance requirement | clean native benchmark and owner decision |
| `backend/common/storage/repositories.py` S3/DynamoDB adapters | not needed by bundle/TMDB local path | deployment migration and external jobs | trace template, Lambda env, scripts, and production runbook |
| `backend/scripts/data_enrichment/` | overlaps prepared/enriched data | whether it is still the supported metadata refresh job | inspect scheduled/manual jobs and data lineage |
| `backend/configs/system.yml` | old S3/native paths | all external invocations of `common.config` and scripts | config consumer map, then staged migration |
| `backend/pipeline/` and old retriever/ranker modules | fallback remains reachable | decision to make bundle mandatory in every environment | deployment smoke and fallback usage telemetry |
| frontend files changed in this worktree | migration-related and actively used | UI/API compatibility after route/schema cleanup | frontend build/API smoke |

## R. Final decision table

| Priority | File/component | Action | Why | Replacement/canonical path | Risk | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | `backend/Dockerfile.lambda`, `template.yaml`, deploy workflow | REFACTOR | deployed image/infra do not package the validated bundle-serving path | bundle-backed Lambda image | High | image start, SAM validate, smoke |
| P0 | `backend/logger/services/mlflow_logger.py` | REFACTOR | import-time optional telemetry can prevent startup | lazy/fail-open bundle-aware telemetry | High | startup matrix + flush test |
| P0 | `backend/api/main.py` | DEPRECATE then DELETE | broken duplicate app imports missing modules | `backend/main.py` | Medium | reference search + API smoke |
| P0 | old retrieval trainer wrappers | DEPRECATE then DELETE | missing builder symbols | `training.retrieval.cli` | Medium | CLI/import/test gates |
| P0 | `features/generate_training_features.py` path | REFACTOR/DELETE symbol | calls missing API and old paths | canonical ranking features | Medium | consumer search + feature pipeline |
| P1 | legacy S3 retrievers/ranker + lifecycle fallback | CONSOLIDATE | two incompatible runtime/artifact contracts | `backend/serving/` bundle | High | deployment/fallback migration |
| P1 | old data/ranking trainers | CONSOLIDATE | duplicate and non-temporal contracts | `backend/data_pipeline/`, `training/ranking/` | Medium/High | regenerated artifacts + metrics |
| P1 | native training/features | DEPRECATE | competing artifact pipeline | Python CLIs unless benchmark justifies native | Medium | clean native build/benchmark |
| P1 | CI deploy workflow | REFACTOR | no test/bundle/image gates | release gates | Medium | workflow-equivalent run |
| P1 | movie route/store fallback | REFACTOR | documented and actual metadata contracts differ | one typed MovieStore resolver | Medium | route edge-case tests |
| P2 | old YAML config family | CONSOLIDATE | stale S3/native/feature ownership | new typed YAML/settings | Medium | config consumer tests |
| P2 | tracked generated JSON | GENERATED / SHOULD NOT BE SOURCE | date-specific generated metadata | data-version manifest | Low | reference/data validation |
| P2 | tracked native ELF binaries | GENERATED / SHOULD NOT BE SOURCE | architecture-specific build outputs | source/build or Python path | Medium | clean build decision |
| P2 | dependency scopes | REFACTOR | training stack installed in serving image | serving/training/dev groups | Medium | image/import/benchmark |
| P2 | mutable legacy scripts | DEPRECATE | overwrite/delete fixed artifacts and S3 keys | canonical CLIs/release tools | Medium | command/reference search |
| P2 | duplicate API schemas | CONSOLIDATE | overlapping response contracts | one public DTO contract | Medium | OpenAPI/frontend tests |
| P3 | README/evaluation/bundle docs | KEEP + DOCUMENT / update later | stale measured/status claims | verified architecture/evaluation docs | Low | docs command audit |
| P3 | frontend and metadata clients | KEEP + DOCUMENT | active user-facing/cold-start responsibilities | existing API/TMDB boundary | Low | frontend/API smoke |

## S. Quantitative cleanup summary

```text
Files inspected: 224 tracked files plus canonical untracked migration files and generated artifact groups
Files confirmed active: 13 responsibility groups
Files marked KEEP: 8 groups
Files marked REFACTOR: 9 groups
Files marked CONSOLIDATE: 6 groups
Files marked DEPRECATE: 8 groups
Files marked GENERATED / SHOULD NOT BE SOURCE: 3 groups
Files safe to DELETE now: 0
Files UNKNOWN: 4 groups
Dead symbols: 3 confirmed, 2 pending consumer verification
Unused dependencies: 0 proven; 1 scope problem and 4 probable training-only scope candidates
Stale configuration entries: 6 configuration groups
Broken entrypoints: 6
Duplicate implementations: 6 responsibility areas
```

## T. Stop condition

The audit can answer the requested questions:

1. **Canonical runtime:** `backend/main.py` → bundle-backed lifecycle → `backend/serving/`.
2. **Canonical data pipeline:** `backend/data_pipeline/` immutable versions and ranking data.

3. **Canonical model training:** `training.retrieval.cli` and `training.ranking.cli`.
4. **Production artifacts:** model trainers publish manifests; `serving.model_bundle` assembles and hashes one release.
5. **Artifact loading:** `serving.model_bundle`/`serving.recommender`.
6. **Active deployment:** GitHub Actions → `backend/Dockerfile.lambda` → SAM, with the bundle-only packaging contract verified by tests.
7. **Genuinely unused code:** native sources, legacy YAML, and the CSV ranker trainer were removed after consumer tracing.
8. **Historical implementations:** S3 retrievers/ranker, old data/ranking trainers, and old wrappers.
9. **Overlaps:** runtime retrieval/ranking, data/features/ranking, schemas, and deployment contracts.
10. **Broken vs dead:** six broken paths are explicitly separated from deletion recommendations.
11. **Dependencies/config:** no dependency is proven unused; scope and ownership cleanup is required.
12. **Documentation:** evaluation, bundle, README, and route docs contain identified drift.
13. **Future evaluation architecture:** keep immutable data, four retrievers, feature schema, ranker, bundle validation, evaluation, smoke, benchmark, and tests.
14. **Safe cleanup order:** contracts → generated hygiene → broken entrypoints → runtime consolidation → training/dependency cleanup → docs/naming.

Per the requested stop condition, the initial audit did not delete, move, rename,
refactor, or rewrite repository files.

## Post-cleanup verification — 2026-08-13

The legacy script/native-header cleanup removed obsolete orchestration files.
The Lambda image contract was then corrected: `backend/Dockerfile.lambda` now
copies only tracked runtime paths and the immutable model bundle. It no longer
copies the retired `pipeline/`, `ranking/`, or native `features/` trees.

Evidence:

- `backend/tests/unit/test_lambda_dockerfile.py` failed against the stale copy
  contract and passes after the correction.
- Full test suite: 106 passed.
- Native sources under `backend/features/native/` and
  `backend/training/*/native/` are now removed; no native source or Makefile
  remains in the supported tree.

Current cleanup summary:

```text
Native source trees: removed
Legacy system/features YAML: removed
Legacy CSV ranker trainer: removed
Lambda retired COPY paths: removed
Full tests: 106 passed
Ruff: passed
```
