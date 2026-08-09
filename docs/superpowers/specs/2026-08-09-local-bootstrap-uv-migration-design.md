# Local Bootstrap and UV Migration Design

## Objective

Make a fresh clone able to prepare its local Python environment, install the
frontend dependencies, and acquire the fixed MovieLens 32M source dataset
without guessing paths or dependency commands.

This change prepares the repository only. It does not preprocess data, train
models, generate model artifacts, start services, validate AWS, or claim that
the recommendation pipelines work.

## Scope

The change will:

- save the completed Phase 0 repository audit at
  `docs/audit/PROJECT_AUDIT.md`;
- make root `pyproject.toml` the only Python dependency declaration;
- commit root `uv.lock` as the only Python dependency lock;
- remove `backend/requirements.txt` and `environment.yml` after dependency
  parity is verified;
- update both backend Dockerfiles to install from `pyproject.toml` and
  `uv.lock` with UV;
- update Docker build commands in GitHub Actions and the Lambda preflight so
  both Dockerfiles receive the root dependency files in their build context;
- keep the frontend on npm and `frontend/package-lock.json`;
- remove `frontend/pnpm-lock.yaml` to eliminate the second frontend lock;
- add an idempotent root `start.sh` for dependency preparation and verified
  MovieLens 32M acquisition;
- add concise bootstrap documentation to the existing README.

The change will not:

- install or redesign the native C++ toolchain;
- run data conversion, enrichment, training, evaluation, ingestion, Docker,
  DynamoDB, FastAPI, Next.js, or AWS commands;
- download model artifacts;
- introduce another task runner, package manager, or configuration layer;
- change recommendation algorithms or serving architecture.

## Dependency Authority

Root `pyproject.toml` will describe the existing Python 3.10 application and
preserve the dependency capabilities currently declared in
`backend/requirements.txt`. The first migration is parity-focused: it must not
opportunistically upgrade, delete, or regroup runtime dependencies in ways that
could change application behavior.

Test-only packages may be placed in UV's `dev` dependency group. Production
Docker builds will install the locked runtime environment without the `dev`
group. CPU PyTorch resolution must remain explicit so UV does not silently
select a CUDA build.

The committed `uv.lock` must resolve successfully for the repository's Python
3.10 target. After parity checks pass, `backend/requirements.txt` and
`environment.yml` will be removed so later changes cannot update one dependency
source while leaving another stale.

Native C++ headers and shared libraries are deliberately excluded. They cannot
be made portable through UV alone, and their future need depends on the planned
training refactor. README and audit text will state this limitation rather than
claim native training readiness.

## Frontend Dependency Authority

The frontend remains an npm project. `frontend/package.json` and
`frontend/package-lock.json` are authoritative, and bootstrap installation uses
`npm ci`. The tracked `frontend/pnpm-lock.yaml` will be removed because keeping
two locks permits different dependency graphs for the same frontend.

The bootstrap will not run the frontend build, lint, tests, or development
server.

## Bootstrap Interface

The repository root will contain executable `start.sh`. Despite its historical
name, its documented responsibility is setup, not service startup.

Running:

```bash
./start.sh
```

will perform these steps in order:

1. Resolve the repository root from the script location so invocation works
   from any current directory.
2. Check for `uv`, `node`, `npm`, `curl`, `unzip`, and an MD5 verification
   command. Missing prerequisites cause an immediate error containing the exact
   missing command; the script will not use `sudo` or execute a remote installer.
3. Run `uv sync --frozen` from the repository root. UV creates and populates
   `.venv` from the committed lock.
4. Run `npm ci --prefix frontend` to reproduce the locked frontend dependency
   tree.
5. Validate whether `backend/data/raw/` already contains the official MovieLens
   32M `movies.csv`, `ratings.csv`, `tags.csv`, and `links.csv` files.
6. If valid files are absent, download the fixed `ml-32m.zip` and companion MD5
   from the official GroupLens dataset host.
7. Verify the archive before extraction. A checksum mismatch deletes only the
   incomplete bootstrap download and exits non-zero without modifying existing
   raw data.
8. Extract into a temporary directory, validate the required files, then move
   the verified dataset files and MovieLens README into
   `backend/data/raw/`. Temporary files are cleaned on exit.
9. Print a short completion summary containing the environment path, dataset
   path, and explicit next commands. No next command is executed automatically.

The fixed source is MovieLens 32M, not `ml-latest`, so repeated clones use the
same published dataset version. The archive URL is:

`https://files.grouplens.org/datasets/movielens/ml-32m.zip`

The checksum source is:

`https://files.grouplens.org/datasets/movielens/ml-32m.zip.md5`

## Idempotency and Data Safety

Repeated bootstrap runs must be safe:

- `uv sync --frozen` reconciles `.venv` to the committed lock;
- `npm ci` reconciles the frontend dependency directory to its lock;
- an already verified MovieLens 32M dataset is not downloaded again;
- downloads use a partial filename and become eligible for extraction only
  after checksum verification;
- extraction occurs outside `backend/data/raw/` before files are moved into
  place;
- the script removes only temporary files it created;
- unrelated files under `backend/data/raw/` are never deleted.

The dataset and download cache remain ignored by Git. No large MovieLens file
will be committed.

## Docker Compatibility

Both backend Dockerfiles currently install `backend/requirements.txt`, so they
must change in the same migration. Each build will copy root `pyproject.toml`
and `uv.lock`, install UV in the image in a pinned way, and run a frozen runtime
sync before copying application code.

Docker build contexts must be adjusted only as required to make the root lock
available. The Lambda image must retain its current Python 3.10 base,
architecture, application entry point, and existing native-runtime handling.
No Docker image will be built by `start.sh`.

The affected build callers are `.github/workflows/deploy.yml` and
`backend/scripts/lambda_preflight.sh`. Root and backend README commands that
still reference `environment.yml`, pip, or `requirements.txt` must be updated in
the same change so no obsolete installation path remains documented.

## Error Handling

The bootstrap uses strict shell error handling and exits non-zero when:

- a required local command is missing;
- the frozen UV environment cannot resolve or install;
- npm's locked installation fails;
- the MovieLens download fails;
- the archive checksum differs from the official checksum;
- the archive lacks any required dataset file;
- verified files cannot be moved into the target directory.

Errors must identify the failed stage and leave existing repository source files
unchanged. The script must not convert an installation or download failure into
a warning followed by a success message.

## Verification Strategy

Implementation will be verified with the smallest checks that cover the new
contracts:

- `bash -n start.sh` for shell syntax;
- a bootstrap test using temporary directories and local fixture downloads so
  idempotency, checksum failure, and required-file validation do not require a
  228 MB network download;
- `uv lock --check` and `uv sync --frozen` for dependency integrity;
- import checks for the backend's principal runtime modules;
- `npm ci`, frontend tests, lint, and build using `package-lock.json`;
- Dockerfile build checks where the local Docker runtime and network are
  available;
- one real official MovieLens 32M download and checksum verification before
  claiming the acquisition path works;
- final `git status` and ignored-file checks to confirm no dataset artifacts are
  staged.

Pipeline training and serving verification remain separate later phases. This
migration will report them as not run rather than treating environment setup as
proof of model correctness.

## Documentation Outcome

The root README will gain one concise local setup section explaining:

- prerequisites;
- `./start.sh`;
- what the script does;
- what it intentionally does not do;
- dataset and environment locations;
- the next existing pipeline commands;
- the deferred native-dependency limitation.

The existing architecture explanation will remain intact.
