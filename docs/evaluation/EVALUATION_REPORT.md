# Offline Evaluation Report

## Initial validated baseline

This is a global-popularity baseline fitted only from `train.parquet` and
evaluated on validation. It is not a retriever, fusion, or LightGBM result.

- Dataset version: `movielens-32m-76a530585bf1`
- Queries: 198,935 validation queries
- Command: `PYTHONPATH=backend UV_CACHE_DIR=/tmp/movie-recs-uv-cache uv run --frozen python -m evaluation.cli popularity`
- Generated artifact: `backend/artifacts/evaluation/20260809T162117Z/`
- Failures: 0

| Metric | @10 | @20 | @50 | @100 | @200 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Recall | 0.037519 | 0.069420 | 0.133767 | 0.212952 | 0.334661 |
| HitRate | 0.295961 | 0.432272 | 0.635152 | 0.761420 | 0.856541 |
| Precision | 0.044448 | 0.042636 | 0.037780 | 0.033398 | 0.028187 |
| Catalog coverage | 0.000174 | 0.000291 | 0.000639 | 0.001221 | 0.002384 |
| User coverage | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

Latency measured only the in-process popularity recommendation call: P50
0.048406 ms, P95 0.051777 ms, and P99 0.054760 ms per query. It excludes
artifact initialization, HTTP, metadata retrieval, feature generation, and
ranking; it is **not** a serving or production latency claim.

## Not yet measured

ALS, TF-IDF, content, two-tower, fusion, LightGBM, ablations, end-to-end
serving latency, and online impact are **NOT YET MEASURED**. The test split has
not been used.
