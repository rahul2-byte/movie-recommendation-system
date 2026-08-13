# File movement plan

This registry is the change boundary for structural refactoring. No file is
moved until every listed consumer is migrated and the verification gate passes.

## Planned moves

| Current path | Target path | Responsibility | Known consumers | Risk |
| --- | --- | --- | --- | --- |
| `backend/common/lifecycle.py` | `backend/application/lifecycle.py` | Application startup and singleton pipeline wiring | migrated: `backend/main.py`, lifecycle tests, bundle startup tests | Medium |
| `backend/common/services/movie_store.py` | `backend/infrastructure/metadata/movie_store.py` | TMDB/catalog metadata access | API movie/catalog routes, lifecycle, serving benchmark, movie-store tests | Medium |
| `backend/common/types.py:Query` | `backend/application/contracts.py:RecommendationQuery` | Request-domain query contract | API recommendation route, serving pipeline, tests | Medium |
| `backend/common/types.py:Candidate` | `backend/retrieval/contracts.py:RetrievalCandidate` | Retrieval candidate contract | integration contract test only today; requires consumer audit | High |
| `backend/serving/recommender.py` | keep initially; split internally later | Candidate collection, fusion, feature assembly, ranker inference | bundle recommender tests, serving pipeline | Medium |
| `backend/data_pipeline/ranking.py` | keep initially; split by tested boundaries later | Ranking-data, candidate, and feature materialization | data-pipeline CLI and integration tests | Medium |

## Deliberately not moving

| Path | Reason |
| --- | --- |
| `backend/training/retrieval/` | Active CLI imports and artifact generation already have a clear owner. |
| `backend/training/ranking/` | Training contract is stable and independent from serving. |
| `backend/evaluation/` | Metrics and baselines already form a coherent domain. |
| `backend/serving/` | Docker, Lambda, smoke, and bundle contracts depend on these paths. |
| `backend/configs/` | Offline CLIs and deployment settings have established paths. |
| `backend/scripts/data_enrichment/` | These are supported executable ingestion tools and are covered by integration tests. |

## Required migration process

For each move:

1. Add or update a focused contract test.
2. Search Python, shell, Docker, CI, SAM, frontend, and documentation consumers.
3. Move the file with history preservation.
4. Update imports and path references.
5. Run Ruff, full pytest, API import, and bundle-load checks.
6. Search for the old path again.
7. Update `BACKEND_STRUCTURE.md` and this registry.

## Stop conditions

Do not move a file when:

- a serialized artifact or deployment path still names the old location;
- the target would create a circular dependency;
- the move changes an API or model artifact contract;
- the consumer list is incomplete;
- behavior-equivalence tests are missing for serving code.
