"""Safety checks for environment-backed runtime settings."""

import pytest
from configuration.settings import Settings


def test_production_settings_reject_wildcard_cors() -> None:
    """Credentialed production requests must use explicit origins."""
    with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
        Settings(ENVIRONMENT="PROD", ALLOWED_ORIGINS="*")


def test_local_settings_allow_wildcard_cors_for_explicit_local_use() -> None:
    """Local development can opt into unrestricted origins deliberately."""
    assert Settings(ENVIRONMENT="LOCAL", ALLOWED_ORIGINS="*").ALLOWED_ORIGINS == ["*"]


def test_imdb_uses_https_for_api_key_requests() -> None:
    """Offline enrichment must not place API keys on clear-text HTTP."""
    assert Settings().IMDB_BASE_URL.startswith("https://")
