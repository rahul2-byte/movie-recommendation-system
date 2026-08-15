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
  --ranker-artifact backend/artifacts/models/ranker/<run-id> \
  --quantization int8
```

Use `--quantization none` for the exact float32 reference bundle, `fp16` for
half-precision FAISS storage, or `int8`, `sq6`, and `sq4` for native scalar
quantization. The builder refuses overwrites, records payload hashes and
quantization metadata, stores uint32 `tmdb_ids.npy` arrays, compacts graph
positions to uint16, and never copies duplicate `item_embeddings.npy` files.
Content joblib payloads are compressed while preserving their serialized
estimator contract. FP8 is intentionally not offered: FAISS has no native
FP8 scalar-quantizer mode.

Startup validation must reject any missing, corrupt, incompatible, or
mixed-version bundle before a recommendation request is served. Compare a
candidate with the reference before promotion:

```bash
PYTHONPATH=backend uv run --frozen python -m serving.compare_bundles \
  --reference-bundle backend/model_bundle/<reference-id> \
  --candidate-bundle backend/model_bundle/<candidate-id> \
  --seed-tmdb-ids 603 238 680 550 13 \
  --limit 20
```

Training and bundle-building commands require the training dependency group;
the Lambda image installs only the serving dependency set:

```bash
uv sync --frozen                 # local development and training
uv sync --frozen --no-default-groups  # serving-only environment
```

The current validated release includes the content-aware `ranking-features-v2`
candidate contract, the LightGBM ranker, and the four-retriever end-to-end
serving path. Promote a bundle only after the manifest, API smoke test, and
latency benchmark pass.

## Compression sweep

The experiment runner trains each graph depth and content dimension once, then
builds the full quantization Cartesian product in an ignored output directory.
The default matrix is graph depths `25,50,100,150,200,300`, content dimensions
`32,64,128,256,384`, and quantization modes `none,fp16,int8,sq6,sq4`.

```bash
PYTHONPATH=backend uv run --frozen python -m evaluation.compression_sweep \
  --output-root /tmp/movie-recs-compression-sweep \
  --config backend/configuration/retrieval_training.yaml \
  --data-config backend/configuration/data_pipeline.yaml \
  --tracking-config backend/configuration/mlflow.yaml \
  --popularity-train-path backend/data/versions/<dataset-version>/train.parquet \
  --als-artifact backend/artifacts/models/als/<run-id> \
  --two-tower-artifact backend/artifacts/models/two_tower/<run-id> \
  --ranker-artifact backend/artifacts/models/ranker/<run-id> \
  --reference-bundle backend/model_bundle/<reference-id> \
  --seed-tmdb-ids 603 238 680 550 13
```

Results are emitted as JSON lines and persisted to `compression-sweep.json`.
The current serving path is capped at 300 candidates, so the sweep reports
Top-100, Top-200, and Top-300 quality; Top-500 requires a separate
candidate-depth change.
