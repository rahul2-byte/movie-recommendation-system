"""Package the production and comparison bundles for a GitHub Release."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from hashing import sha256
from serving.model_bundle import load_model_bundle


def _package(source: Path, destination: Path) -> None:
    """Create a zstd archive whose root is the bundle payload itself."""
    load_model_bundle(source)
    subprocess.run(
        [
            "tar",
            "--zstd",
            "-cf",
            str(destination),
            "-C",
            str(source),
            ".",
        ],
        check=True,
    )


def main() -> None:
    """Create immutable INT8/SQ6 release archives and their manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-bundle", type=Path, required=True)
    parser.add_argument("--comparison-bundle", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite release directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    production_name = "movie-recs-bundle-int8-graph200-content256-v1.tar.zst"
    comparison_name = "movie-recs-bundle-sq6-graph200-content256-v1.tar.zst"
    _package(args.production_bundle.resolve(), output_dir / production_name)
    _package(args.comparison_bundle.resolve(), output_dir / comparison_name)

    manifest = {
        "schema_version": "production-release-v1",
        "release_id": args.release_id,
        "assets": {
            "production": {
                "filename": production_name,
                "sha256": sha256(output_dir / production_name),
                "quantization": "int8",
                "graph_depth": 200,
                "content_dimension": 256,
            },
            "comparison": {
                "filename": comparison_name,
                "sha256": sha256(output_dir / comparison_name),
                "quantization": "sq6",
                "graph_depth": 200,
                "content_dimension": 256,
            },
        },
    }
    (output_dir / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
