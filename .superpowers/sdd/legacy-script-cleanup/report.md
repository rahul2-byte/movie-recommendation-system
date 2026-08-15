# Legacy script cleanup

Removed obsolete native/S3 orchestration scripts and unused retrieval-native
headers. Retained deployment, backend startup, enrichment, and canonical data
pipeline entrypoints. Removed the Docker startup ingestion branch because its
`ingest_data.py` dependency was retired and bundle serving uses MovieStore/TMDB
metadata instead.

Verification: repository reference search, full test suite, Ruff, and diff
checks.
