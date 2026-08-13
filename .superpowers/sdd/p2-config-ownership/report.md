# Configuration ownership cleanup

Removed the unreferenced legacy `configs/ranker.yml`. Ranking configuration is
owned by `ranking_training.yaml` and `ranking_features.yaml`. Legacy
`system.yml` and `features.yml` remain because the explicitly retained fallback
and native scripts still consume them.

Verification: config ownership test, full unit suite, Ruff, and diff checks.
