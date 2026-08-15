# P0 Lambda Bundle Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package and validate the immutable model bundle in the Lambda image so production uses the same serving path as local execution.

**Architecture:** The Lambda image receives one explicit relative bundle directory at build time, copies it to `/var/task/model_bundle`, and sets `MODEL_BUNDLE_DIR` to that path. Static tests prevent Docker/SAM/CI drift; an optional image smoke check verifies imported runtime behavior.

**Tech Stack:** Docker, AWS Lambda Python 3.10 base image, FastAPI/Mangum, Pytest, model-bundle-v1.

## Global Constraints

* Do not add S3 model downloads or change retriever/ranker logic.
* Do not delete legacy modules or S3/SAM parameters in this task.
* `MODEL_BUNDLE_DIR` equals `/var/task/model_bundle` in Lambda.
* `MODEL_BUNDLE_PATH` is an explicit path relative to Docker build context.
* Add regression tests before production code.

---

### Task 1: Add the Lambda bundle contract

**Files:**

* Create: `backend/tests/unit/test_lambda_bundle_packaging.py`
* Modify: `backend/Dockerfile.lambda`
* Modify: `template.yaml`

**Interfaces:** consumes `MODEL_BUNDLE_PATH`; produces `/var/task/model_bundle` and `MODEL_BUNDLE_DIR=/var/task/model_bundle`.

- [ ] Write a failing test asserting the Dockerfile declares `ARG MODEL_BUNDLE_PATH`, copies `backend/main.py`, `backend/serving/`, and `COPY ${MODEL_BUNDLE_PATH}/`, and declares the exact environment path. Assert that SAM declares the same environment path.
- [ ] Run `UV_CACHE_DIR=/tmp/movie-recs-uv-cache uv run --frozen pytest backend/tests/unit/test_lambda_bundle_packaging.py -q`; confirm it fails.
- [ ] Implement only the stated Dockerfile/SAM contract. Retain legacy package copies because lifecycle still imports the fallback modules.
- [ ] Re-run the focused test; confirm it passes.
- [ ] Commit with `fix: package model bundle in lambda image`.

### Task 2: Require the bundle during deployment builds

**Files:**

* Modify: `backend/Dockerfile.lambda`
* Modify: `.github/workflows/deploy.yml`
* Test: `backend/tests/unit/test_lambda_bundle_packaging.py`

**Interfaces:** CI passes `--build-arg MODEL_BUNDLE_PATH=<one explicit path>`; Docker fails if `/var/task/model_bundle/bundle_manifest.json` is absent.

- [ ] Extend the failing test to assert a manifest guard and an explicit CI build argument.
- [ ] Run the focused test; confirm it fails.
- [ ] Add the minimal Docker manifest guard and CI build argument. The workflow must fail clearly when the release bundle is not in its build context; do not invent a remote model store.
- [ ] Re-run the focused test; confirm it passes.
- [ ] Commit with `ci: require explicit lambda model bundle`.

### Task 3: Validate the release contract

**Files:**

* Test: `backend/tests/unit/test_lambda_bundle_packaging.py`
* Test: `backend/tests/unit/test_bundle_startup.py`

- [ ] Run `UV_CACHE_DIR=/tmp/movie-recs-uv-cache PYTHONPATH=backend uv run --frozen pytest backend/tests/unit/test_lambda_bundle_packaging.py backend/tests/unit/test_bundle_startup.py -q`.
- [ ] When Docker is available, build with `--build-arg MODEL_BUNDLE_PATH=backend/model_bundle/movielens-32m-4retriever-ranker-v1`; run `python -c "import main; print(main.app.title)"` in the image.
- [ ] Run `UV_CACHE_DIR=/tmp/movie-recs-uv-cache uv run --frozen pytest backend/tests/unit -q`; report any unrelated existing failures separately.

## Plan self-review

The task only establishes the bundle image contract. It neither removes legacy runtime code nor changes algorithms, data, ranking features, or model publication.
