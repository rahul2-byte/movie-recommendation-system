# Local Bootstrap and UV Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a fresh clone reproducibly install the existing Python and frontend dependencies and acquire the fixed MovieLens 32M dataset without running project pipelines or services.

**Architecture:** A root `pyproject.toml` and committed `uv.lock` become the sole Python dependency authority. One strict, idempotent root shell script runs frozen UV/npm installs and performs checksum-verified, temporary extraction of MovieLens 32M; Docker consumes the same root lock. The script is exercised through real subprocess behavior with fake local command binaries so tests require neither package nor dataset downloads.

**Tech Stack:** UV 0.11.6, Python 3.10, Bash, npm/`package-lock.json`, Docker, MovieLens 32M.

## Global Constraints

- Work only on `chore/local-uv-bootstrap`; do not commit without explicit user authorization.
- Root `pyproject.toml` and `uv.lock` are the sole Python dependency declarations.
- Preserve the runtime capabilities declared by `backend/requirements.txt`; do not opportunistically refactor application dependencies.
- Keep the frontend on npm and `frontend/package-lock.json`; remove `frontend/pnpm-lock.yaml` only after npm verification.
- `start.sh` prepares dependencies and data only; it must not run conversion, enrichment, training, evaluation, ingestion, Docker, databases, APIs, or frontend services.
- Download only fixed MovieLens 32M from `https://files.grouplens.org/datasets/movielens/ml-32m.zip` and verify it with `https://files.grouplens.org/datasets/movielens/ml-32m.zip.md5`.
- Do not install or refactor native C++ dependencies in this milestone.
- Preserve both Docker images' Python 3.10 base, Lambda entry point, and current native-runtime handling.

---

### Task 1: Establish the root UV dependency authority

**Files:**
- Create: `pyproject.toml`
- Create: `uv.lock`

**Interfaces:**
- Consumes: the dependency capabilities in `backend/requirements.txt` and the Python 3.10 Docker base.
- Produces: `uv sync --frozen` for local/dev installs and `uv sync --frozen --no-dev --no-install-project` for runtime installs.

- [ ] **Step 1: Create the parity-focused project metadata**

Define Python `>=3.10,<3.11`; keep every non-test package from `backend/requirements.txt`; move `pytest` and `pytest-asyncio` into `[dependency-groups].dev`; configure an explicit CPU PyTorch index and `torch==2.5.1+cpu`.

- [ ] **Step 2: Generate the lock**

Run: `uv lock`

Expected: exit 0 and a root `uv.lock` resolving the Python 3.10 graph.

- [ ] **Step 3: Verify the frozen environment**

Run: `uv lock --check && uv sync --frozen`

Expected: both commands exit 0 and `.venv` is created/reconciled.

- [ ] **Step 4: Verify principal imports**

Run:

```bash
PYTHONPATH=backend uv run --frozen -- python -c "import fastapi, faiss, lightgbm, pandas, pyarrow, torch; import main; print('backend imports ok')"
```

Expected: exit 0 and `backend imports ok`.

### Task 2: Add the setup-only bootstrap with test-first behavior

**Files:**
- Create: `tests/test_start.sh`
- Create: `start.sh`

**Interfaces:**
- Consumes: root `pyproject.toml`, `uv.lock`, `frontend/package-lock.json`, local commands `uv`, `node`, `npm`, `curl`, `unzip`, and either `md5sum` or `md5`.
- Produces: `.venv`, `frontend/node_modules`, and verified `backend/data/raw/{movies.csv,ratings.csv,tags.csv,links.csv,README.txt}`.

- [ ] **Step 1: Write the failing subprocess test**

Create a temporary repository fixture containing the dependency manifests and fake `uv`, `node`, `npm`, `curl`, `unzip`, and `md5sum` commands. Assert that the first run installs dependencies and moves all required files, a second run performs no download, a wrong checksum exits non-zero without modifying existing raw data, and a missing archive member exits non-zero.

- [ ] **Step 2: Run the test and verify RED**

Run: `bash tests/test_start.sh`

Expected: non-zero because `start.sh` does not exist.

- [ ] **Step 3: Implement the minimal bootstrap**

Use `set -euo pipefail`, resolve the root through `BASH_SOURCE`, validate prerequisites, run `uv sync --frozen` and `npm ci --prefix frontend`, validate existing files against the official per-file MD5 values recorded in MovieLens 32M `README.txt`, and otherwise download/check/extract in `mktemp -d` before installing files. A trap removes only the temporary directory.

- [ ] **Step 4: Run test and syntax verification**

Run: `bash -n start.sh && bash tests/test_start.sh`

Expected: exit 0 with all bootstrap cases passing.

### Task 3: Make Docker consume the same root lock

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `backend/Dockerfile.lambda`
- Modify: `.github/workflows/deploy.yml`
- Modify: `backend/scripts/lambda_preflight.sh`

**Interfaces:**
- Consumes: root `pyproject.toml` and `uv.lock` from root Docker build context.
- Produces: both backend images install the frozen runtime graph without the dev group.

- [ ] **Step 1: Update Docker build contexts**

Keep `.github/workflows/deploy.yml` and `lambda_preflight.sh` behavior unchanged except changing their final build context from `backend/` to `.`.

- [ ] **Step 2: Update both Dockerfiles**

Pin UV to `0.11.6`; copy root `pyproject.toml` and `uv.lock`; run `uv sync --frozen --no-dev --no-install-project`; copy `.venv` into the runtime image where applicable; prepend `.venv/bin` to `PATH`; retain existing `libgomp`, app-copy, and entry-point behavior.

- [ ] **Step 3: Validate Docker definitions**

Run: `docker build -f backend/Dockerfile.lambda .`

Expected: exit 0 if Docker daemon and registry network are available. If unavailable, report Docker build as not verified rather than claiming success.

### Task 4: Remove duplicate manifests and document the one setup path

**Files:**
- Delete: `backend/requirements.txt`
- Delete: `environment.yml`
- Delete: `frontend/pnpm-lock.yaml`
- Modify: `README.md`
- Modify: `backend/README.md`

**Interfaces:**
- Consumes: verified UV/npm/Docker dependency paths from Tasks 1–3.
- Produces: one documented local bootstrap command and no stale Python/frontend dependency authority.

- [ ] **Step 1: Install and verify npm lock**

Run: `npm ci --prefix frontend`

Expected: exit 0.

- [ ] **Step 2: Run frontend checks**

Run: `npm test --prefix frontend -- --runInBand && npm run lint --prefix frontend && npm run build --prefix frontend`

Expected: all commands exit 0. Existing unrelated failures must be reported and must not be hidden by this migration.

- [ ] **Step 3: Remove duplicate dependency files**

Delete the two legacy Python manifests and the pnpm lock only after the UV/npm checks above pass.

- [ ] **Step 4: Update documentation**

Add a concise root local-setup section covering prerequisites, `./start.sh`, output locations, intentional exclusions, and the deferred native dependency limitation. Replace backend pip instructions with `uv sync --frozen` from the repository root.

- [ ] **Step 5: Run final verification**

Run:

```bash
bash -n start.sh
bash tests/test_start.sh
uv lock --check
uv sync --frozen
PYTHONPATH=backend uv run --frozen -- python -c "import fastapi, faiss, lightgbm, pandas, pyarrow, torch; import main; print('backend imports ok')"
npm test --prefix frontend -- --runInBand
npm run lint --prefix frontend
npm run build --prefix frontend
git diff --check
git status --short
```

Expected: all executable checks exit 0; status shows only reviewed migration/audit/plan changes and no dataset/model artifacts.

