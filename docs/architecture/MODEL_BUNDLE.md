# Immutable runtime model bundle

The new runtime package is a manually released, ignored directory under
`backend/model_bundle/<bundle-id>/`. It is baked into the same Docker image
used locally and by Lambda; serving does not download models from S3.

Build only after fitting all four retrievers and a ranker from the same dataset
version and feature schema:

```bash
PYTHONPATH=backend uv run --frozen python -m serving.model_bundle \
  --output-dir backend/model_bundle/<bundle-id> \
  --als-artifact backend/artifacts/models/als/<run-id> \
  --item-graph-artifact backend/artifacts/models/item_graph/<run-id> \
  --two-tower-artifact backend/artifacts/models/two_tower/<run-id> \
  --content-artifact backend/artifacts/models/content/<run-id> \
  --ranker-artifact backend/artifacts/models/ranker/<run-id>
```

The builder refuses overwrites, records payload hashes, and stores compact
`tmdb_ids.npy` arrays instead of duplicate `item_embeddings.npy` files. Startup
validation must reject any missing, corrupt, incompatible, or mixed-version
bundle before a recommendation request is served.

The current release gate is intentionally incomplete until the content-aware
`ranking-features-v2` candidates, ranker, and end-to-end serving tests are
generated. Do not use this bundle builder to promote the existing three-source
ranker.
