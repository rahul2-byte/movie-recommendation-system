# Current Repository Structure Audit

This is the post-cleanup structure, not the historical structure described in
the original audit evidence.

```text
backend/
  api/                 HTTP routes and request/response schemas
  application/         startup and application-level contracts
  common/              settings, logging, and external API clients
  configs/              typed/runtime and offline pipeline configuration
  data_pipeline/       ingestion, temporal data, enrichment, and ranking data
  evaluation/          offline metrics, baselines, and evaluation runners
  infrastructure/      metadata adapters used by the application
  logger/              optional MLflow telemetry
  retrieval/           retrieval-domain contracts and shared retrieval helpers
  serving/              bundle loading, candidate fusion, ranking, and smoke tools
  training/             canonical retrieval and ranking trainers
  scripts/              supported ingestion and deployment orchestration
  tests/                unit and integration verification
frontend/               Next.js client
docs/                   architecture, deployment, evaluation, audit, and refactoring docs
```

## Canonical runtime path

`main.py` -> `api/v1` -> `application.lifecycle` -> `serving.pipeline` ->
`serving.recommender` -> four retrievers + ranker -> `infrastructure.metadata`.

## Canonical offline path

`data_pipeline.cli` -> `training.retrieval.cli` and `training.ranking.cli` ->
`serving.model_bundle` -> local/Lambda bundle serving.

## Findings

- Runtime and training code are separated.
- Enrichment storage and movie schemas are owned by `data_pipeline`.
- External metadata adapters are owned by `infrastructure`.
- Candidate fusion is isolated as pure serving logic.
- `data_pipeline/ranking.py` remains one module because its stages share
  resumability, schemas, hashing, and Parquet helpers.
- CI now fails early when required bundle files are absent.
