# Data and Feature Engineering

## Source data

The source is MovieLens 32M plus a TMDB-enriched metadata snapshot. The canonical dataset version is `movielens-32m-76a530585bf1`.

| Measure | Value | Evidence |
|---|---:|---|
| Enriched catalog rows | 86,007 | Dataset documentation and manifest |
| Ratings retained | 31,890,244 | Dataset documentation |
| Tags retained | 1,987,406 | Dataset documentation |
| Positive rows after deduplication | 26,189,978 | Dataset manifest |
| Train rows | 15,695,937 | Dataset manifest |
| Validation rows | 198,935 | Dataset manifest |
| Test rows | 198,935 | Dataset manifest |
| Eligible users | 198,935 | Dataset manifest |
| Excluded users | 1,957 | Dataset manifest |

## Data contract

`tmdb_id` is the operational ID. `movielens_id` is retained for lineage. `item_index` is the dense internal model index.

Preparation removes invalid or ambiguous MovieLens/TMDB mappings, writes compressed Parquet, records input hashes, and creates a versioned manifest.

## Split protocol

The split is per-user chronological:

- positive event: latest deduplicated rating at least `3.0`;
- minimum positive history: `8`;
- minimum training history: `6`;
- train/validation/test proportions: `60% / 20% / remaining`;
- equal timestamps are not split across a boundary;
- validation seeds are the five most recent train positives;
- test seeds are the five most recent pre-test positives.

This prevents a user’s future interaction from entering that same user’s training history. It is not a single global deployment-date simulation.

## Ranking features

| Feature family | Meaning |
|---|---|
| Retrieval source count | Number of retrievers returning the item |
| Per-source rank | Position within ALS, graph, two-tower, or content results |
| Reciprocal rank | `1 / rank`, used as a comparable rank-derived signal |
| Candidate interaction count | Positive training interactions for the item |
| Log interaction count | `log1p` popularity feature |

The ranker consumes 11 features in the exact order declared by `backend/configuration/ranking_features.yaml`. A schema change requires retraining and bundle regeneration.

## Missing measurements

Catalog distributions, feature missingness rates, drift, and the effect of metadata exclusions are not currently benchmarked. They should be added before claiming production data-quality coverage.
