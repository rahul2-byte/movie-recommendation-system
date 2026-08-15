# Configuration cleanup complete

Established explicit ownership for the canonical YAML/settings family and
documented the remaining legacy boundary. New pipeline code owns the data,
retrieval, ranking, evaluation, and tracking YAML files; `settings.py` owns
runtime environment values. `system.yml` and `features.yml` remain only for
the retained legacy fallback/native stack and are blocked from new consumers.

Verification: config ownership test, full unit suite, Ruff, and diff checks.
