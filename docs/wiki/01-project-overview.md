# Project Overview

## Product goal

The product answers: “What should I watch next based on these movies?” The user curates five seed movies in the frontend. The backend returns a ranked, display-ready list of movies.

The operational identifier is the TMDB ID. MovieLens IDs remain lineage fields in the offline dataset.

## User journey

1. The user searches the TMDB-backed catalog.
2. The user selects up to five seed movies.
3. Optional mood/genre labels are collected by the UI.
4. The frontend posts seed TMDB IDs and a result limit.
5. The backend retrieves and ranks candidates.
6. TMDB metadata is returned and rendered as recommendation cards.

## Important current limitation

The API accepts `moods`, but `backend/api/v1/recommend.py` does not pass them into the serving pipeline and `BundleRecommender` does not use them. Mood selection is therefore collected but has no current ranking effect.

## Repository ownership

| Responsibility | Canonical location |
|---|---|
| HTTP routes and schemas | `backend/api/` |
| Lazy runtime construction | `backend/application/lifecycle.py` |
| Dataset preparation and splitting | `backend/data_pipeline/` |
| Offline training | `backend/training/` |
| Offline metrics and baselines | `backend/evaluation/` |
| Bundle loading and inference | `backend/serving/` |
| TMDB and external HTTP | `backend/infrastructure/` |
| Frontend experience | `frontend/src/` |
| Deployment | `backend/Dockerfile.lambda`, `template.yaml`, `.github/workflows/deploy.yml` |

## Non-goals

The current repository does not prove persistent user profiles, online learning, A/B testing, click-through optimization, or a live production traffic volume.
