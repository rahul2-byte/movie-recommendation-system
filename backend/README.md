# Backend

The backend serves recommendations from one immutable model bundle:

```text
FastAPI/Lambda -> api/v1 -> common.lifecycle -> serving.BundleRecommender
             -> four retrievers + LightGBM ranker -> MovieStore/TMDB metadata
```

Canonical commands are `data_pipeline.cli`, `training.retrieval.cli`,
`training.ranking.cli`, `evaluation.cli`, and `serving.model_bundle`. The
bundle is loaded from `MODEL_BUNDLE_DIR`; startup fails if it is unset.

Directories:

- `api/`: HTTP boundary.
- `common/`: runtime settings, metadata clients, enrichment, and lifecycle.
- `configs/`: canonical pipeline configuration and documented legacy inputs.
- `data_pipeline/`: immutable preparation, temporal splits, and ranking data.
- `training/`: retrieval and ranking trainers.
- `evaluation/`: offline metrics and baselines.
- `serving/`: bundle loading, fusion, ranking, and release smoke checks.
- `features/native/` and `training/*/native/`: unsupported native experiment
  sources; binaries are build outputs and are not committed.
