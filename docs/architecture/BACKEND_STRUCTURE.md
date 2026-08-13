# Backend Structure

This is the target structure for incremental refactoring. Existing runtime
packages remain in place until their replacement is tested; do not perform a
large package move merely to match this document.

```text
backend/
  api/             FastAPI request/response transport
  common/          shared runtime contracts, clients, and storage adapters
  configs/         version-controlled YAML configuration
  data/
    raw/           ignored downloaded source inputs
    versions/       ignored immutable prepared/split datasets
  data_pipeline/   authoritative ETL, validation, manifests, and MLflow hooks
  evaluation/      pure metrics, baselines, evaluation runners, and CLI
  features/        train-serving shared feature transformations
  ranking/         ranking inference and future reproducible training support
  retrieval/       retrieval inference and model implementations
  training/        future authoritative Python training entry points
  tests/
    unit/          pure logic and isolated component contracts
    integration/   Parquet, MLflow, pipeline, and cross-module contracts
  artifacts/       ignored MLflow, evaluation, and model outputs
  scripts/         legacy utilities only; not authoritative pipeline entry points
```

## Dependency rules

- `api/` orchestrates runtime packages but does not contain model or ETL logic.
- `data_pipeline/`, `training/`, and `evaluation/` share stable data contracts;
  they do not import API routes.
- `features/` owns transformations shared by training and inference.
- `configs/` controls behavior; `data/versions/` and `artifacts/` are generated,
  immutable or ignored outputs.
- Tests import backend packages through root pytest configuration. Run
  `uv run --frozen pytest` without `PYTHONPATH=backend`.

## Migration rule

Refactor one boundary at a time: add/adjust tests, move or replace the bounded
component, run unit and integration tests, then update this document. Legacy
native and duplicate paths remain marked unsupported until the replacement
training pipeline has been validated.
