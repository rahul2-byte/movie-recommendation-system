# Configuration ownership

The repository has one canonical configuration family for the bundle-backed
pipeline:

- `data_pipeline.yaml`: dataset preparation and temporal split rules.
- `retrieval_training.yaml`: retriever training parameters.
- `ranking_data.yaml`: ranking-event and candidate construction parameters.
- `ranking_features.yaml`: ranking feature schema and serialization.
- `ranking_training.yaml`: LightGBM ranking parameters.
- `evaluation.yaml`: offline evaluation parameters.
- `mlflow.yaml`: experiment tracking defaults.
- `settings.py`: runtime environment variables and secrets only.

`system.yml` and `features.yml` are legacy compatibility inputs for the old
S3/native fallback stack. They are intentionally retained until that stack is
retired; new code must not add consumers to them. `ranker.yml` was removed
because it had no consumers.
