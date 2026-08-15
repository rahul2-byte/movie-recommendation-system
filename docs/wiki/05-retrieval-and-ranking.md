# Retrieval, Fusion, and Ranking

## Why multiple stages

Retrieval optimizes recall: it finds a manageable candidate set. Ranking optimizes ordering: it scores only those candidates. Ranking cannot recover an item that retrieval omitted.

## Candidate generation

For each seed, each retriever requests up to 200 candidates. Results are merged by TMDB ID, seeds are excluded, and the candidate pool is capped at 300 before LightGBM scoring.

## Reciprocal-rank fusion

For a candidate with rank `r` from a source, the rank-derived contribution is:

```text
1 / (60 + r)
```

The implementation uses ranks rather than raw similarities because the four retrievers have incompatible score scales. Source agreement becomes an explicit ranking feature through `retrieval_source_count`.

## Ranking flow

```text
per-seed results
  → source deduplication
  → reciprocal-rank fusion
  → 11 ranking features
  → LightGBM score
  → descending sort
  → metadata enrichment
```

## Implemented filtering

- invalid/non-positive IDs are ignored;
- seed IDs are excluded;
- duplicate candidates are removed;
- missing metadata records are omitted;
- final output is capped at the requested limit.

There is no implemented diversity re-ranker, novelty constraint, genre-balancing pass, or explicit business-rule re-ranker.

## Measured individual retrieval evidence

Latest timestamped validation artifacts contain 198,935 queries and zero recorded retrieval failures.

| Retriever | Recall@10 | Recall@100 | P50 | P95 | P99 |
|---|---:|---:|---:|---:|---:|
| ALS | 0.063379 | 0.351757 | 0.332 ms | 0.358 ms | 0.375 ms |
| Item graph | 0.058041 | 0.273285 | 0.330 ms | 0.358 ms | 0.371 ms |
| Two-tower | 0.052333 | 0.297732 | 0.317 ms | 0.351 ms | 0.365 ms |
| Content | 0.004477 | 0.019587 | 0.332 ms | 0.361 ms | 0.376 ms |
| TF-IDF | 0.006705 | 0.022532 | 0.339 ms | 0.369 ms | 0.386 ms |

These are offline in-process timings, not Lambda production latency.
