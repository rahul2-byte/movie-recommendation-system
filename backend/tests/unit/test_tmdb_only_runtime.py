"""Regression checks for the TMDB-only serving architecture."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_local_runtime_does_not_require_dynamodb() -> None:
    """Serving metadata comes from TMDB, not a local DynamoDB container."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    startup = (ROOT / "backend" / "scripts" / "start_backend.sh").read_text(
        encoding="utf-8"
    )

    assert "database:" not in compose
    assert "DynamoDB" not in startup
    assert "boto3" not in startup
