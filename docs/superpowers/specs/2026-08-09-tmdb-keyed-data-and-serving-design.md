# TMDB-Keyed Data and Serving Design

## Decision

The recommendation system keeps its trained retrieval and ranking models.
TMDB is the sole production source for movie metadata. DynamoDB, MovieLens CSVs,
and the offline enriched metadata snapshot are not runtime metadata sources.

Offline training uses the MovieLens 32M interactions and the supplied enriched
metadata snapshot. Every operational item identifier in processed datasets,
model ID maps, retrieval candidates, feature rows, and API requests is
`tmdb_id`. MovieLens `movieId` remains lineage only (`movielens_id`) and must
not be exposed as an operational recommendation ID.

## Data Contract

`backend/data/raw/` remains immutable source input. The deterministic builder
writes Zstandard-compressed Parquet to `backend/data/processed/`:

| Output | Purpose | Identity columns |
| --- | --- | --- |
| `movies.parquet` / `links.parquet` | lossless source conversions | `movieId` only; lineage inputs |
| `catalog.parquet` | canonical trainable movie catalog | `tmdb_id`, `movielens_id`, `item_index` |
| `ratings.parquet` | trainable interactions | `user_id`, `tmdb_id`, `movielens_id`, `rating`, `timestamp` |
| `tags.parquet` | trainable tags | `user_id`, `tmdb_id`, `movielens_id`, `tag`, `timestamp` |
| `movies_enriched.parquet` | static training metadata | `tmdb_id`, `movielens_id` |
| `manifest.json` | reproducibility and exclusion record | dataset/schema metadata |

`item_index` is a dense, deterministic, internal integer index. It exists
because native arrays and embedding tables cannot safely use sparse TMDB IDs as
positions. It is never an API ID.

Only one-to-one MovieLens-to-TMDB mappings with matching enriched metadata are
admitted to the canonical catalog. The manifest records excluded unmapped,
ambiguous, and metadata-missing records. No accuracy claim is made from this
filter until evaluation is run.

## Production Flow

```text
TMDB seed IDs -> live TMDB metadata -> trained retrievers / fusion ->
TMDB candidate metadata -> LightGBM ranker -> TMDB-ID recommendations
```

For catalog-known seeds, all retrievers use S3-loaded artifacts whose ID maps
are keyed by `tmdb_id`. For a seed absent from a collaborative artifact,
collaborative retrievers skip it. The content retriever must later encode live
TMDB metadata using its persisted preprocessing artifact so an all-new seed can
still produce trained-catalog candidates. TMDB recommendation/similar endpoints
are not candidate generators in this design.

## Boundaries and Failure Behaviour

- TMDB failure means metadata-dependent requests fail clearly; the system does
  not silently substitute stale metadata.
- An unknown seed never aliases a MovieLens ID.
- S3 holds model artifacts and their TMDB-ID maps, not a movie metadata replica.
- DynamoDB removal occurs only after the TMDB-backed serving path, artifact
compatibility validation, and API tests pass.

## Scope Sequence

1. Establish the Parquet/canonical-ID contract and tests.
2. Migrate Python training builders and emitted artifact maps to `tmdb_id`.
3. Migrate runtime API, retrieval, feature, and ranking paths to TMDB IDs and
   live TMDB metadata; remove DynamoDB deployment/code paths.
4. Refactor or retire native/C++ paths after measuring which remain necessary.
5. Run the leakage-safe evaluation and serving benchmarks before claiming model
   quality or performance.

## Non-goals

- No TMDB metadata database, cache service, or new infrastructure.
- No claim that dropping records has no accuracy impact.
- No replacement of the existing model architecture.
