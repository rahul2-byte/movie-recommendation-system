# P1 metadata route contract

The TMDB movie route now delegates exclusively to `MovieStore.get_by_tmdb_id`.
The route no longer reaches into nonexistent `imdb_client` state or duplicates
TMDB normalization and image mapping. The public route paths are unchanged.

Verification: route edge-case tests, full unit suite, Ruff, and diff checks.
