# P0 Lambda Bundle Packaging Design

## Goal

Make the Lambda image run the same immutable model-bundle serving path as local Uvicorn, without runtime S3 model downloads.

## Scope

This task changes only Lambda image packaging and release validation. It does not remove the legacy S3 fallback, change retriever/ranker behavior, or design model-bundle publication for CI.

## Design

The Lambda Dockerfile accepts one required `MODEL_BUNDLE_PATH` build argument relative to the Docker build context. It copies `backend/main.py`, `backend/serving/`, and that single bundle directory to `/var/task`, then sets `MODEL_BUNDLE_DIR=/var/task/model_bundle`.

The Docker build must fail if the copied bundle lacks `bundle_manifest.json`. SAM provides the same runtime path. Existing S3 parameters remain untouched because the legacy fallback is still reachable and is a later consolidation task.

## Validation

Tests check the Dockerfile/SAM contract before production edits. When Docker is available, an image built with the local release bundle imports `main` with the bundle path configured. No model payload is added to Git.

## Constraints

* Do not add a new S3 model-loading path.
* Do not delete legacy modules or S3/SAM parameters.
* Do not use an implicit `latest` bundle path.
* Write regression tests before production changes.
