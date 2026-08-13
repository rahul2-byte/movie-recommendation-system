"""Content-addressed dataset version identifiers and JSON manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from data_pipeline.config import DataPipelineConfig


def canonical_json(value: Any) -> str:
    """Serialize manifest content deterministically for hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _current_implementation_fingerprint() -> str:
    """Hash the ETL modules whose behavior determines dataset contents."""
    directory = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for filename in ("config.py", "manifests.py", "prepare.py", "split.py"):
        path = directory / filename
        digest.update(filename.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def implementation_fingerprint() -> str:
    """Hash ETL implementation files that affect derived dataset contents."""
    return _current_implementation_fingerprint()


def dataset_version_id(
    config: DataPipelineConfig,
    source_hashes: dict[str, str],
    *,
    implementation_fingerprint: str | None = None,
) -> str:
    """Create a content-addressed dataset version identifier."""
    payload = {
        "config": config.version_payload(),
        "source_hashes": source_hashes,
        "implementation_fingerprint": implementation_fingerprint
        or _current_implementation_fingerprint(),
    }
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:12]
    return f"{config.dataset.name}-{digest}"


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write a manifest atomically so interrupted jobs cannot publish partial state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
