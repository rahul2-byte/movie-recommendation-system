# Deployment contract

The local and Lambda deployments use the same image and the same immutable
production model bundle. Local compression experiments and the comparison
bundle never enter the production image.

```text
GitHub Release assets -> CI hash validation -> production bundle staging
                      -> Docker build argument -> /var/task/model_bundle
                      -> MODEL_BUNDLE_DIR
```

Lambda does not download model artifacts at runtime. GitHub Release assets are
downloaded only during CI image construction. ECR stores the deployable Docker
image and SAM deploys Lambda from its immutable `ImageUri`. DynamoDB stores
operational movie metadata, while TMDB is the fallback metadata provider when a
record is unavailable locally.

The production release contains two bundles for validation:

- graph-200/content-256/INT8: embedded in Lambda;
- graph-200/content-256/SQ6: comparison-only, never copied into Lambda.

## Publish a model release

Build the two immutable assets from the selected local bundles, then publish
the generated directory as a GitHub Release. The release tag is the only model
version the deployment workflow consumes:

```bash
PYTHONPATH=backend uv run --frozen python \
  backend/scripts/package_release_bundles.py \
  --production-bundle .cache/movie-recs-compression-sweep/bundles/graph-200-content-256-int8 \
  --comparison-bundle /tmp/movie-recs-native-quant-test/sq6 \
  --release-id movie-recs-v1 \
  --output-dir /tmp/movie-recs-release-v1

gh release create movie-recs-v1 \
  /tmp/movie-recs-release-v1/release-manifest.json \
  /tmp/movie-recs-release-v1/movie-recs-bundle-int8-graph200-content256-v1.tar.zst \
  /tmp/movie-recs-release-v1/movie-recs-bundle-sq6-graph200-content256-v1.tar.zst \
  --title "Movie recommender model release movie-recs-v1" \
  --notes "Production INT8 bundle plus SQ6 comparison bundle."
```

Set the repository variable `MODEL_RELEASE_TAG=movie-recs-v1`, or provide the
same tag through the manual workflow input. CI validates both archives, embeds
only INT8 in the Lambda image, and uploads comparison metrics as a workflow
artifact.

## Release gates

1. Download a tagged GitHub Release and verify both bundle archive hashes.
2. Validate both extracted bundle manifests and compare INT8 with SQ6.
3. Run Ruff format/check and the complete pytest suite.
4. Build `backend/Dockerfile.lambda` with only the INT8 bundle.
5. Start the image and invoke `/ping` through the Lambda runtime endpoint.
6. Run the recommendation smoke check with five seed TMDB IDs.
7. Push the image to ECR and deploy with SAM using only image, environment, metadata,
   and CORS parameters.

The CI workflow enforces the static quality gates. Docker and SAM require the
network-enabled release environment because dependency installation occurs in
the image builder stage.

## Generated local state

Local MLflow SQLite state and enriched JSON exports are generated during
development and are not release inputs. The data pipeline recreates them when
needed; production serving uses the immutable model bundle instead.
