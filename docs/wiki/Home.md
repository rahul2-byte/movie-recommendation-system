# Movie Recommendation System

## What is built

This is a seed-based hybrid movie discovery system. A user selects up to five movies they like; the backend retrieves candidates with four offline-trained retrieval models, fuses their ranks, applies a LightGBM ranker, enriches the result with TMDB metadata, and returns the final list to a Next.js frontend.

This is not a persistent user-ID recommender. The online request is conditioned on the selected TMDB movie IDs.

## Current status

| Area | Status |
|---|---|
| Data preparation | Implemented and versioned |
| Chronological validation split | Implemented |
| ALS, item graph, two-tower, content retrieval | Implemented |
| LightGBM LambdaRank | Implemented |
| Bundle validation and compression | Implemented |
| Local FastAPI serving | Implemented |
| Lambda/ECR/SAM deployment path | Configured and tested locally; live deployment evidence is not in this repository |
| Online engagement evaluation | Not implemented |

## System at a glance

```mermaid
flowchart LR
  A[MovieLens + TMDB data] --> B[Versioned data pipeline]
  B --> C[Retrieval training]
  C --> D[Ranking training]
  D --> E[Immutable model bundle]
  E --> F[FastAPI / Lambda]
  F --> G[ALS + graph + two-tower + content]
  G --> H[RRF fusion]
  H --> I[LightGBM ranking]
  I --> J[TMDB metadata]
  J --> K[Next.js website]
```

## Evidence conventions

- **Implemented:** present in the current source path.
- **Measured:** backed by a generated artifact or benchmark.
- **Inferred:** follows from code but is not directly benchmarked.
- **Recommended:** future work, not current behavior.

## Navigate

- [Project overview](01-project-overview.md)
- [System architecture](02-system-architecture.md)
- [Data and features](03-data-and-features.md)
- [Training and models](04-training-and-models.md)
- [Retrieval and ranking](05-retrieval-and-ranking.md)
- [Evaluation and experiments](06-evaluation-and-experiments.md)
- [Compression and artifacts](07-compression-and-artifacts.md)
- [Serving, API, and frontend](08-serving-api-frontend.md)
- [Deployment, reliability, and monitoring](09-deployment-reliability.md)
- [Reproducibility and roadmap](10-reproducibility-roadmap.md)
