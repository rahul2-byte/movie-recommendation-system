# Compression and Artifact Management

## Bundle contract

The immutable bundle contains:

- `bundle_manifest.json`;
- four retriever payloads and ID mappings;
- LightGBM model and feature schema;
- popularity feature state;
- quantization metadata;
- hashes for payload and source manifests.

The bundle records dataset version `movielens-32m-76a530585bf1`, ID schema `tmdb-keyed-v1`, model-bundle schema `model-bundle-v2`, candidate limit `300`, and RRF rank constant `60`.

## Selected compression configuration

The documented release target is graph depth `200`, content dimension `256`, and INT8 quantization. The compression sweep produced a 123,048,393-byte bundle for that configuration.

INT8 reduces the sweep bundle relative to the unquantized variant by approximately 41.0%:

```text
(208,456,514 - 123,048,393) / 208,456,514 = 40.97%
```

## Component shape

The large components are content SVD/vectorizer state, content FAISS storage, and item-graph neighbor storage. ALS and two-tower indexes are comparatively small after quantization.

The repository also contains local `int8-v2` and `fp16-v2` bundles. Their on-disk sizes differ from the compression-sweep output, so the exact promoted release identity must be verified from the release manifest before production claims are made.

## Build and compare

```bash
ALS_ARTIFACT=backend/artifacts/models/als/<run-id>
ITEM_GRAPH_ARTIFACT=backend/artifacts/models/item_graph/<run-id>
TWO_TOWER_ARTIFACT=backend/artifacts/models/two_tower/<run-id>
CONTENT_ARTIFACT=backend/artifacts/models/content/<run-id>
RANKER_ARTIFACT=backend/artifacts/models/ranker/<run-id>

PYTHONPATH=backend uv run --frozen python -m serving.model_bundle \
  --output-dir backend/model_bundle/$BUNDLE_ID \
  --als-artifact "$ALS_ARTIFACT" \
  --item-graph-artifact "$ITEM_GRAPH_ARTIFACT" \
  --two-tower-artifact "$TWO_TOWER_ARTIFACT" \
  --content-artifact "$CONTENT_ARTIFACT" \
  --ranker-artifact "$RANKER_ARTIFACT" \
  --quantization int8
```

```bash
REFERENCE_BUNDLE=backend/model_bundle/<reference-id>
CANDIDATE_BUNDLE=backend/model_bundle/<candidate-id>

PYTHONPATH=backend uv run --frozen python -m serving.compare_bundles \
  --reference-bundle "$REFERENCE_BUNDLE" \
  --candidate-bundle "$CANDIDATE_BUNDLE" \
  --seed-tmdb-ids 603 238 680 550 13 \
  --limit 20
```

## Compatibility rules

Startup must reject missing, corrupt, mixed-version, hash-mismatched, or feature-schema-incompatible bundles. FAISS positions must always resolve through the matching TMDB-ID array.
