# Serving, API, and Frontend Integration

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/ping` | Health response |
| GET | `/api/v1/movies/search?q=...` | TMDB movie search |
| GET | `/api/v1/movies/{movie_id}` | Movie lookup |
| GET | `/api/v1/catalog/trending` | Trending catalog |
| GET | `/api/v1/catalog/popular` | Popular catalog |
| GET | `/api/v1/catalog/new` | New-release catalog |
| POST | `/api/v1/recommend` | Seed-based recommendations |

## Recommendation request

```json
{
  "seed_tmdb_ids": [603, 238, 680, 550, 13],
  "moods": ["DARK"],
  "limit": 20
}
```

Validation requires one to five positive TMDB IDs. `limit` is bounded from 1 to 150; the frontend sends 20.

## Recommendation response

```json
{
  "recommendations": [
    {
      "tmdbId": 123,
      "title": "Example",
      "year": 1999,
      "genres": ["Drama"],
      "posterUrl": "https://image.tmdb.org/t/p/w342/example.jpg",
      "rating": 7.8,
      "rankScore": 0.921
    }
  ]
}
```

`rating` is the TMDB vote average. `rankScore` is the raw LightGBM ordering
score; it is not a probability, confidence value, similarity percentage, or
user-facing star rating.

## Frontend flow

The homepage recommendation builder collects one to five selected movies.
`fetchRecommendations()` posts to `/recommend`; the shared API client prefixes
`/api/v1`; React Query stores the result in the Zustand recommendation store;
`/recommendations` renders the result grid. `/setup` remains a compatibility
redirect to the homepage builder.

Catalog routes use frontend revalidation hints, but recommendation calls are request-driven and are not statically cached.

## Local serving

```bash
export MODEL_BUNDLE_DIR="$PWD/model_bundle/$BUNDLE_ID"

cd backend
PYTHONPATH=. uv run --frozen python -m uvicorn main:app \
  --host 0.0.0.0 --port 8080
```

Without `MODEL_BUNDLE_DIR`, catalog/search routes can work, but recommendation requests fail because the bundle-backed pipeline is mandatory.

## External metadata behavior

TMDB calls use an async connection pool, rate limiting, retries, and a process-local cache. The current cache has no documented TTL or hit-ratio measurement. Individual candidate lookup failures are logged and omitted.
