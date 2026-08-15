# Repository Restructure Report

## Scope

This report records the completed structural cleanup and the P1/P2 follow-up.
Recommendation behavior, retriever mathematics, ranker features, and artifact
schemas were preserved.

## Completed changes

- Moved lifecycle orchestration to `backend/application/`.
- Moved metadata adapters to `backend/infrastructure/metadata/`.
- Split application and retrieval contracts.
- Isolated serving candidate collection and reciprocal-rank fusion.
- Moved movie schemas, enrichment, checkpoints, Parquet output, and dataset
  merging under `backend/data_pipeline/`.
- Removed the unused MovieLens ID mapper and empty legacy service package.
- Added Lambda packaging for `backend/application/`.
- Added CI/local preflight checks for all bundle manifests, ranker payloads,
  and feature schema.

## Historical audit clarification

The original audit documents contain evidence from before cleanup. References
to native/C++ trainers, old S3 artifact paths, `common.lifecycle`, and removed
feature/ranking modules describe historical findings; they are not active
runtime paths. The current supported training path is the Python CLI pipeline
and the current serving path is the immutable four-retriever bundle.

## Remaining risk

The bundle is intentionally ignored because it contains generated model
payloads. A release process must therefore make the bundle available to CI
before Docker build, or publish it through an approved artifact-release step.

## Verification

The repository-wide verification gate is Ruff, pytest, API import, bundle
smoke, frontend production build, `sam validate`, and Docker Lambda build and
startup. Results are recorded separately when tooling or network access is
unavailable.

## Verification results (2026-08-14)

- Ruff: passed.
- Backend tests: `110 passed`.
- API import: passed.
- Frontend `npm run build`: passed; static generation logged expected warnings
  because the local backend was not running.
- `sam validate`: not run because the SAM CLI is unavailable in this environment.
- Docker Lambda build: attempted with host networking; blocked while Amazon
  Linux attempted to resolve its package mirror. This is an environment
  network blocker, not a source verification pass.
