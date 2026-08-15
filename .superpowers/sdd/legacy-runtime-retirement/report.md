# Legacy runtime retirement

Retired the old S3/DynamoDB recommendation runtime: legacy retrievers, recall,
feature builder, ranker, pipeline, and artifact repositories were removed.
`common.lifecycle` now requires `MODEL_BUNDLE_DIR` and serves only the
validated immutable bundle. The TMDB ID integration test now covers the active
API contract, and backend documentation describes the bundle-only path.

Native C++ sources remain as unsupported experiment sources; generated binaries
are not tracked.

Verification: full unit/integration suite, Ruff, diff check, and repository
reference search.
