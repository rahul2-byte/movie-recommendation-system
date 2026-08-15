"""Validate downloaded production and comparison model-release assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from hashing import sha256
from serving.model_bundle import load_model_bundle


def _read_object(path: Path) -> dict[str, Any]:
    """Read one required JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _validate_bundle(path: Path, expected_quantization: str) -> dict[str, Any]:
    """Validate bundle hashes and the release model-selection contract."""
    bundle = load_model_bundle(path)
    manifest = bundle.manifest
    if manifest.get("quantization") != expected_quantization:
        raise ValueError(
            f"{path} quantization is {manifest.get('quantization')!r}; "
            f"expected {expected_quantization!r}"
        )
    graph_manifest = _read_object(path / "retrievers/item_graph/manifest.json")
    content_manifest = _read_object(path / "retrievers/content/manifest.json")
    if graph_manifest.get("neighbor_count") != 200:
        raise ValueError(f"{path} does not contain the graph-200 artifact")
    if content_manifest.get("embedding_dim") != 256:
        raise ValueError(f"{path} does not contain the content-256 artifact")
    return {
        "path": str(path),
        "bytes": sum(file.stat().st_size for file in path.rglob("*") if file.is_file()),
        "dataset_version": manifest.get("dataset_version"),
        "quantization": manifest.get("quantization"),
        "graph_depth": graph_manifest.get("neighbor_count"),
        "content_dimension": content_manifest.get("embedding_dim"),
    }


def main() -> None:
    """Verify release archive hashes and extracted bundle contracts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--production-dir", type=Path, required=True)
    parser.add_argument("--comparison-dir", type=Path, required=True)
    args = parser.parse_args()

    release_dir = args.release_dir.resolve()
    release_manifest = _read_object(release_dir / "release-manifest.json")
    if release_manifest.get("schema_version") != "production-release-v1":
        raise ValueError("Unsupported release manifest schema")
    assets = release_manifest.get("assets")
    if not isinstance(assets, dict):
        raise ValueError("Release manifest must contain an assets object")
    for role in ("production", "comparison"):
        asset = assets.get(role)
        if not isinstance(asset, dict):
            raise ValueError(f"Release manifest is missing {role} asset metadata")
        asset_path = release_dir / str(asset.get("filename", ""))
        expected_hash = str(asset.get("sha256", ""))
        if not asset_path.is_file() or not expected_hash:
            raise FileNotFoundError(f"Missing release asset for {role}: {asset_path}")
        if sha256(asset_path) != expected_hash:
            raise ValueError(f"SHA256 mismatch for release asset: {asset_path}")

    production = _validate_bundle(args.production_dir.resolve(), "int8")
    comparison = _validate_bundle(args.comparison_dir.resolve(), "sq6")
    if production["dataset_version"] != comparison["dataset_version"]:
        raise ValueError("Production and comparison bundles use different datasets")
    print(json.dumps({"production": production, "comparison": comparison}, sort_keys=True))


if __name__ == "__main__":
    main()
