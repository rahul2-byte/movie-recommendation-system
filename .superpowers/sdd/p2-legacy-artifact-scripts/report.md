# Legacy artifact scripts

Removed `upload_artifacts.py` and `verify_models.py`. Both targeted the old
mutable S3/system.yml artifact contract and had no active runtime, CI, or
supported documentation consumers. Bundle creation, validation, and release
checks remain under `serving.model_bundle`, `serving.smoke`, and deployment
gates.

Verification: orphan-entrypoint regression test, full unit suite, Ruff, and
diff checks.
