# P1 lifecycle boundary

`common.lifecycle` now imports the legacy S3/feature/ranking stack only when
the bundle path is absent. Bundle-backed startup keeps the canonical serving
imports and no longer loads competing legacy modules unnecessarily. The legacy
fallback remains available temporarily for migration compatibility.

Verification: bundle lifecycle/startup tests, full unit suite, Ruff, and diff
checks.
