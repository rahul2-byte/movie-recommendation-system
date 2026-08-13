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

Legacy compatibility configuration was removed with the retired S3/native
fallback stack. Runtime settings live in `settings.py`; offline pipeline
settings are loaded explicitly from the YAML files listed above.

YAML keys describe offline pipeline contracts. Environment settings remain
uppercase because they mirror deployment variables. The supported runtime
requires `MODEL_BUNDLE_DIR` to point to an immutable model bundle.

Runtime model artifacts are never downloaded from S3. The Lambda image contains
the validated bundle; DynamoDB and TMDB are used only for movie metadata.
