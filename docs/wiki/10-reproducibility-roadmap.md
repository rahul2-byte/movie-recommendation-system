# Reproducibility and Roadmap

## Reproduce the data pipeline

```bash
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli prepare
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli split
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli validate
```

The pipeline records source hashes, configuration hashes, implementation fingerprints, output hashes, and dataset version IDs.

## Reproduce evaluation

```bash
PYTHONPATH=backend uv run --frozen python -m evaluation.cli popularity
PYTHONPATH=backend uv run --frozen python -m evaluation.cli popularity --partition test --final-evaluation
```

Evaluation outputs are written under ignored, timestamped artifact directories. The test partition must not be used for iterative model selection.

## Reproduce serving checks

```bash
PYTHONPATH=backend uv run --frozen python -m serving.serving_smoke_test \
  --base-url http://127.0.0.1:8080 \
  --seed-tmdb-ids 603 238 680 550 13
```

```bash
export BUNDLE_DIR=backend/model_bundle/$BUNDLE_ID

PYTHONPATH=backend uv run --frozen python -m serving.benchmark \
  --bundle-dir "$BUNDLE_DIR" \
  --base-url http://127.0.0.1:8080 \
  --seed-tmdb-ids 603 238 680 550 13
```

## Model and data versioning

Compatibility is defined by:

```text
Git SHA
  + dataset version
  + training configuration hash
  + feature code/configuration hashes
  + model manifest hashes
  + bundle schema version
  + ID schema version
```

## Roadmap

### P0 — correctness and release evidence

- Measure the final test split.
- Verify the exact promoted bundle against its release manifest.
- Run Lambda cold/warm smoke and latency checks.
- Correct documentation that implies moods already affect ranking.

### P1 — high-value production evidence

- Add end-to-end latency breakdown and concurrency benchmarks.
- Measure compression variants with Recall/NDCG, not only list overlap.
- Add metadata failure-rate and cache-hit telemetry.
- Add recommendation-quality regression gates.

### P2 — product and reliability improvements

- Implement mood-aware ranking features or remove the unused mood contract.
- Add diversity, novelty, and catalog-coverage metrics.
- Add explicit cold-start policies and tests.
- Add model/data drift checks.

### P3 — research

- Distillation or lower-dimensional content representations.
- Learned calibration across retrievers.
- Online experimentation and engagement optimization.

## Honest limitations

The repository demonstrates a complete offline-to-serving architecture, but it does not yet prove live production traffic, online business impact, Lambda-scale throughput, or long-term drift behavior.
