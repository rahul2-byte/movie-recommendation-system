# Deployment contract

The local and Lambda deployments use the same image and the same immutable
model bundle.

```text
model training -> serving.model_bundle -> Docker build argument
               -> /var/task/model_bundle -> MODEL_BUNDLE_DIR
```

Lambda does not download model artifacts from S3. S3 is not part of the model
serving contract. DynamoDB stores operational movie metadata, while TMDB is the
fallback metadata provider when a record is unavailable locally.

## Release gates

1. Build the bundle and verify `bundle_manifest.json`.
2. Run Ruff format/check and the complete pytest suite.
3. Build `backend/Dockerfile.lambda` with the bundle build argument.
4. Start the image and invoke `/ping` through the Lambda runtime endpoint.
5. Run the recommendation smoke check with five seed TMDB IDs.
6. Push the image and deploy with SAM using only image, environment, metadata,
   and CORS parameters.

The CI workflow enforces the static quality gates. Docker and SAM require the
network-enabled release environment because dependency installation occurs in
the image builder stage.
