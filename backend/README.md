# Backend

The backend exposes the recommendation API locally through FastAPI and can be
packaged for AWS Lambda through the `main.handler` Mangum entrypoint.

The online request path is:

```text
FastAPI/Lambda
  -> api/v1
  -> application.lifecycle
  -> serving.BundleRecommender
  -> ALS, item-graph, two-tower, and content retrieval
  -> reciprocal-rank fusion
  -> LightGBM ranking
  -> TMDB metadata enrichment
```

Training is offline. Online requests load an immutable model bundle and do not
run training or rebuild indexes.

## Runtime requirements

Recommendation requests require `MODEL_BUNDLE_DIR` to point to a validated
model bundle. Without it, catalog and search routes may still work, but
recommendation requests fail during pipeline initialization.

Local serving:

```bash
MODEL_BUNDLE_DIR="$PWD/backend/model_bundle/<bundle-id>" \
PYTHONPATH=backend uv run --frozen python -m uvicorn main:app \
  --host 0.0.0.0 --port 8080
```

The Lambda container sets `MODEL_BUNDLE_DIR=/var/task/model_bundle` and uses:

```text
main.handler
```

## Package ownership

- `api/`: FastAPI routes and typed request/response schemas.
- `application/`: process-level lifecycle and recommendation pipeline creation.
- `common/`: shared models, logging, and common services.
- `configuration/`: runtime settings and offline YAML configuration.
- `data_pipeline/`: dataset preparation, enrichment, validation, and splits.
- `evaluation/`: offline metrics, baselines, and evaluation CLIs.
- `features/`: ranking feature construction and feature contracts.
- `infrastructure/`: external service and metadata boundaries.
- `ranking/`: runtime ranking and ranking inference components.
- `retrieval/`: retrieval implementations and model code.
- `serving/`: bundle loading, candidate fusion, ranking orchestration, and
  serving smoke tests.
- `training/`: retrieval and ranking training CLIs.

## Supported offline commands

These are the supported module-level entrypoints:

```text
data_pipeline.cli          Prepare, split, and validate data
training.retrieval.cli     Train retrieval models
training.ranking.cli       Build ranking data and train LightGBM
evaluation.cli              Run offline metrics and baselines
serving.model_bundle        Build and validate serving bundles
```

Example commands and configuration ownership are documented in the
[training](../docs/wiki/04-training-and-models.md),
[evaluation](../docs/wiki/06-evaluation-and-experiments.md), and
[configuration](configuration/README.md) pages.

## Configuration

Offline pipeline configuration lives in `configuration/` YAML files, including
data preparation, retrieval training, ranking data, ranking features, ranking
training, evaluation, and MLflow settings. Runtime environment variables and
secrets are defined in `configuration/settings.py`.

The serving bundle is packaged with the runtime image. Movie metadata is
resolved through the infrastructure metadata boundary, including TMDB-backed
metadata access where configured.

For the complete architecture, deployment model, and failure behavior, see the
[backend serving documentation](../docs/wiki/08-serving-api-frontend.md) and
[deployment documentation](../docs/wiki/09-deployment-reliability.md).
