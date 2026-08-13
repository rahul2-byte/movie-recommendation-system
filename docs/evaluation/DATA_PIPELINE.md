# Versioned Data Pipeline

The supported offline data path is `backend.data_pipeline`. Do not use the
legacy/native scripts listed in `docs/audit/PROJECT_AUDIT.md`.

## Commands

Run from the repository root:

```bash
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli prepare
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli split
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli validate
PYTHONPATH=backend uv run --frozen python -m data_pipeline.cli status
```

`prepare` creates a content-addressed version beneath `backend/data/versions/`.
`split` uses the newest prepared version unless `--dataset-version <version>` is
provided. `validate` and `status` use the newest complete version by default.

The completed version contains `catalog.parquet`, `train.parquet`,
`validation.parquet`, `test.parquet`, and `manifest.json`. The four Parquet files
are the final model/evaluation data contract; transient checkpoints remain under
the version's ignored `.work/` directory and permit resume after interruption.

The commands log progress and create local MLflow runs in
`backend/artifacts/mlflow/`. The manifest records the source hashes, configuration
hash, split timestamps, output hashes, row counts, and resume state.
