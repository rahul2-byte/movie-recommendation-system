# Structure and Clarity Refactor Plan

## Scope

The existing package layout already separates API, data preparation, training,
evaluation, and serving. This plan improves names and contracts without moving
working algorithms or changing recommendation behavior.

## Canonical boundaries

```text
api -> common.lifecycle -> serving -> common.services
data_pipeline -> training -> serving.model_bundle
evaluation -> metrics/baselines/fusion/runners
```

`backend/retrieval/seeded.py` remains the shared seed-wise retrieval utility.
`backend/scripts/data_enrichment/` remains supported ingestion tooling, not a
second model-training pipeline.

## Migration order

1. Fix API schema contracts and add regression tests.
2. Establish terminology in `docs/architecture/GLOSSARY.md`.
3. Rename ambiguous private locals and add focused public docstrings.
4. Remove confirmed orphan modules and stale lint exceptions.
5. Rename `build_tfidf.py` only if its import migration is demonstrated to be
   low-risk; otherwise retain the stable path and document its dual TF-IDF and
   metadata-content responsibility.
6. Re-run repository-wide path, import, test, and runtime checks.

## Non-goals

- No algorithm changes.
- No new abstraction layer for one implementation.
- No broad package move solely for aesthetics.
- No compatibility alias for a removed legacy path.

## Verification gate

Each stage must pass Ruff, unit tests, integration tests, API import, bundle
smoke, and the existing training smoke commands before the next stage begins.
