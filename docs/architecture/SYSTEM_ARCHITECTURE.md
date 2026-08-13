# System architecture

The repository has two deliberately separate flows: an offline model-building
flow and an online bundle-serving flow. Both are anchored by immutable dataset,
feature, and model manifests.

## Online request flow

```text
Frontend
  -> backend/main.py
    -> api/v1 routes
      -> application.lifecycle
        -> serving.pipeline
          -> serving.recommender
            -> ALS, item graph, two-tower, content retrievers
            -> rank fusion and LightGBM ranking
          -> common.services.movie_store
            -> infrastructure.metadata.MovieStore
              -> DynamoDB/catalog metadata
              -> TMDB fallback metadata
        -> API response
```

`MODEL_BUNDLE_DIR` is required. The bundle contains retriever indexes,
retriever manifests, ranker state, feature schema, and popularity state. Model
payloads are loaded once per process and reused across warm requests.

## Offline model flow

```text
MovieLens/TMDB-enriched raw data
  -> data_pipeline.prepare
  -> data_pipeline.split
  -> data_pipeline.ranking
  -> training.retrieval.cli
       ALS / item graph / two-tower / TF-IDF-content
  -> data_pipeline ranking candidates/features
  -> training.ranking.cli
       LightGBM LambdaRank
  -> serving.model_bundle
       immutable four-retriever + ranker release
```

## Responsibility boundaries

| Domain | Canonical owner | Must not own |
| --- | --- | --- |
| HTTP transport | `backend/api/` | retrieval mathematics or data preparation |
| Request orchestration | `backend/application/lifecycle.py` and `backend/serving/pipeline.py` | model training |
| Request contract | `backend/application/contracts.py` | retrieval implementation details |
| Metadata access | `backend/infrastructure/metadata/movie_store.py` | candidate scoring |
| Retrieval contract | `backend/retrieval/contracts.py` | HTTP transport concerns |
| Dataset preparation | `backend/data_pipeline/` | HTTP or AWS deployment |
| Retrieval training | `backend/training/retrieval/` | request handling |
| Ranking training | `backend/training/ranking/` | metadata network calls |
| Offline evaluation | `backend/evaluation/` | API startup |
| Online model loading | `backend/serving/model_bundle.py` | dataset preparation |
| Online retrieval/ranking | `backend/serving/` | raw AWS SDK access |
| Deployment | `template.yaml`, Docker, workflow | recommendation algorithms |

## Dependency direction

```text
api -> application/runtime orchestration -> serving/domain contracts
training/data_pipeline -> shared contracts and manifests
serving -> artifact loaders and metadata contracts
infrastructure/external clients -> application boundaries
evaluation -> pure metrics and reproducible artifacts
```

Core metrics, retrieval utilities, and ranking feature calculations must remain
usable without FastAPI, Lambda, DynamoDB, or network access.

## Invariants

- Seed movie IDs are TMDB IDs and are never returned as recommendations.
- Candidate IDs are deduplicated before final ranking output.
- Feature order is part of the ranker artifact contract.
- FAISS positions are resolved through the artifact's TMDB-ID mapping.
- All four retrievers and the ranker in a release bundle share a compatible
  dataset/schema contract.
- A failed optional metadata lookup removes that record, not the entire batch.
