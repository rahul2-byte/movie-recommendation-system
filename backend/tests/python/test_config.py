import pytest
from common.config import config

def test_config_structure():
    """Verify that essential config sections exist."""
    assert "system" in config
    assert "settings" in config
    assert "ranker" in config
    assert "features" in config

def test_config_interpolation():
    """Verify that ${data_root} and other placeholders are interpolated."""
    # Based on system.yml: ratings_path: "${data_root}/processed/ratings.parquet"
    data_root = config.system.data_root
    ratings_path = config.system.ratings_path
    assert data_root in ratings_path
    assert "${" not in ratings_path

def test_settings_environment():
    """Verify settings correctly reflect environment."""
    assert config.settings.ENVIRONMENT in ["LOCAL", "PROD"]
    assert hasattr(config.settings, "ALLOWED_ORIGINS")
    assert isinstance(config.settings.ALLOWED_ORIGINS, list)
