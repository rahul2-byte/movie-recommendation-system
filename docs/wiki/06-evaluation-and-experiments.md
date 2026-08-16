# Evaluation and Experiments

## Evaluation protocol

The evaluator uses validation by default and requires an explicit flag for the final test partition:

```bash
PYTHONPATH=backend uv run --frozen python -m evaluation.cli popularity
PYTHONPATH=backend uv run --frozen python -m evaluation.cli popularity --partition test --final-evaluation
```

The current protocol measures recovery of later positive ratings (`>=3.0`). It is not a strict “liked movie” judgment and does not represent online engagement.

## Baseline and ranker results

The ranker manifest contains validation comparisons:

| System | NDCG@10 | MAP@10 | MRR@10 |
|---|---:|---:|---:|
| Popularity | 0.179199 | 0.118712 | 0.125135 |
| RRF | 0.276502 | 0.192482 | 0.210940 |
| LightGBM | 0.281976 | 0.195100 | 0.213656 |

Source: `backend/artifacts/models/ranker/20260810T185410Z/manifest.json`.

The LightGBM validation improvement over popularity is:

| Metric | Absolute | Relative |
|---|---:|---:|
| NDCG@10 | +0.102777 | +57.38% |
| MAP@10 | +0.076387 | +64.34% |
| MRR@10 | +0.088521 | +70.73% |

These are validation comparisons, not online business metrics.

## Popularity baseline

Measured validation baseline:

| Metric | @10 | @20 | @50 | @100 | @200 |
|---|---:|---:|---:|---:|---:|
| Recall | 0.037519 | 0.069420 | 0.133767 | 0.212952 | 0.334661 |
| Hit rate | 0.295961 | 0.432272 | 0.635152 | 0.761420 | 0.856541 |

## Compression overlap experiment

The compression sweep compares recommendation-list overlap against a reference bundle. For graph depth `200` and content dimension `256`:

| Variant | Bytes | Top-100 Jaccard | Top-200 Jaccard | Top-300 Jaccard |
|---|---:|---:|---:|---:|
| None | 208,456,514 | 1.0000 | 1.0000 | 0.9802 |
| FP16 | 151,515,849 | 1.0000 | 1.0000 | 0.9802 |
| INT8 | 123,048,393 | 1.0000 | 1.0000 | 1.0000 |
| SQ6 | 115,930,757 | 1.0000 | 0.9704 | 0.9481 |
| SQ4 | 108,813,125 | 0.9608 | 0.9417 | 0.8127 |

Jaccard is a stability signal, not Recall, NDCG, or user satisfaction. Compression quality metrics on the held-out test split are not yet measured.

## Not implemented

There is no online A/B test, click-through metric, watch-start metric, completion metric, diversity metric, novelty metric, or production drift report in the repository.
