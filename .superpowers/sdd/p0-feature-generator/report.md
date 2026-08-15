# P0 obsolete feature generator

Removed `backend/features/generate_training_features.py`. It was unreachable
from runtime, training, CI, and supported CLI paths, depended on the missing
`FeatureBuilder.from_paths` API, and consumed obsolete processed-data paths.

The canonical ranking feature pipeline remains in `backend/data_pipeline` and
`backend/training/ranking/features.py`.

Verification: focused regression test passes after deletion; full unit suite
and `git diff --check` run before merge.
