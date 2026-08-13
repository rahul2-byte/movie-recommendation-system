# Duplicate schema and generated metadata cleanup

Removed the unused `api/schemas/movie.py` module; active routes use
`api/schemas/recommend.py`, while data/enrichment uses `common.models.movie`.
Removed the unreferenced generated `data/processed/movies_enriched.json`
summary; version manifests remain the reproducible metadata source.

The raw summary file remains untouched pending provenance verification.

Verification: regression test, full unit suite, Ruff, and diff checks.
