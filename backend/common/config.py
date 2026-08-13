from types import SimpleNamespace

from configs import settings

# Runtime configuration is environment-backed. Offline pipeline settings are
# loaded explicitly by their CLIs from the canonical YAML files.
config = SimpleNamespace(settings=settings)
