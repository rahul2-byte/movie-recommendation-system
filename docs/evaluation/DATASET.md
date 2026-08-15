# Dataset Preparation

## Source

MovieLens 32M source files in `backend/data/raw/` were converted locally with:

```bash
PYTHONPATH=backend uv run --frozen python backend/scripts/data_enrichment/csv_to_parquet.py
```

The generated files are ignored by Git and live in `backend/data/processed/`.
Their exact source SHA-256 hashes and transformation contract are in
`backend/data/processed/manifest.json`.

## Observed Conversion Result

| Measure | Value |
| --- | ---: |
| Canonical enriched TMDB catalog rows | 86,007 |
| Ratings retained | 31,890,244 |
| Tags retained | 1,987,406 |
| Unmapped MovieLens link rows excluded | 124 |
| Ambiguous TMDB mapping rows excluded | 72 |
| Link/enriched metadata mismatch rows excluded | 1,382 |

All outputs use Zstandard compression level 3. `tmdb_id` is the operational
identifier; `movielens_id` is retained only as lineage; `item_index` is a dense
internal model index.

These are data-preparation counts, not recommendation-quality metrics.
Recall, ranking quality, and the effect of exclusions are **NOT YET MEASURED**.
