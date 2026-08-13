"""Compatibility facade exposing environment-backed runtime settings."""

from types import SimpleNamespace

from configs import settings

# Runtime configuration is environment-backed. Offline pipeline settings are
# loaded explicitly by their CLIs from the canonical YAML files.
config = SimpleNamespace(settings=settings)
"""Compatibility settings facade for clients that predate typed settings."""
"""Shared configuration helpers used by application and training code."""
