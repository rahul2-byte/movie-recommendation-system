# Training and Model Architecture

## Training commands

Canonical training is Python-based:

```bash
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli als
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli item_graph
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli two_tower
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli content
```

The ranking trainer consumes immutable ranking feature artifacts:

```bash
PYTHONPATH=backend uv run --frozen python -m training.ranking.cli \
  --train-feature-dir <train-feature-dir> \
  --validation-feature-dir <validation-feature-dir>
```

## Retrieval configurations

| Model | Configuration |
|---|---|
| ALS | 64 factors, alpha `20.0`, regularization `0.1`, 15 iterations |
| Item graph | 200 neighbors, BM25 graph, `k1=1.2`, `b=0.75` |
| Two-tower | 64-dimensional embeddings, batch `8192`, 3 epochs, learning rate `0.003` |
| Content | TF-IDF max features `75,000`, SVD dimension `256`, weighted metadata fields |

## Two-tower concept

The two-tower trainer learns an embedding for each item and optimizes related interaction pairs. At serving time, the stored item vectors are searched with cosine similarity. The current online seed experience uses the selected movie vectors as retrieval queries; it does not construct a persistent user tower from a user account.

## ALS concept

ALS factorizes positive user–movie interaction structure into latent factors. The item factors are indexed for similarity retrieval. The serving path uses item-side vectors for seed-based candidate generation.

## Item graph concept

The item graph stores a fixed neighbor list per item. Neighbors are generated from binary positive interaction co-occurrence and ranked with a BM25-style weighting. The online path uses the graph as a fast discrete lookup rather than running graph construction.

## Content concept

Metadata fields are converted into weighted text tokens. TF-IDF followed by SVD creates dense item vectors. A metadata-only seed can be embedded at request time when it is not present in the trained index; this is the content retriever’s cold-start path.

## Ranking training

LightGBM uses the `lambdarank` objective, learning rate `0.05`, 31 leaves, L2 regularization `1.0`, up to 300 boosting rounds, and early stopping after 30 rounds. The final artifact records the best iteration and feature schema hash.

Training duration, peak memory, hardware utilization, and repeatability across machines are not consistently measured in the current artifacts.
