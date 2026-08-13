# Python Two-Tower Trainer Audit

Date: 2026-08-10

## Finding

The former Python entry point `backend/training/retrieval/train_two_tower.py`
imports `TwoTowerBuilder`, which does not exist. It is not an executable
training path. The native trainer and the previous serving retriever also
averaged all selected seed vectors; this conflicts with the established
per-seed candidate-generation contract.

## Authoritative replacement

`python -m training.retrieval.cli two_tower` trains an item-candidate
two-tower model only from versioned `train.parquet`. It creates positive pairs
from chronological adjacent interactions, in both directions, with a capped
number of adjacent pairs per user configured in
`backend/configs/retrieval_training.yaml`. It uses deterministic sampled
negatives and writes the same TMDB-keyed embedding, FAISS, ID-map, and manifest
artifact contract used by the offline evaluator.

At serving and offline evaluation time, each seed is retrieved separately and
candidate lists are combined by seed support and best per-seed rank. No
five-seed average is used.

## Status of legacy paths

`train_two_tower.py` and `backend/training/retrieval/native/` are retained for
forensics only. They are not authoritative and must not be used for training
or evidence generation until separately audited and tested.

## Reproduction

```bash
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli two_tower --ci
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli two_tower
```

Both commands use dataset version `movielens-32m-76a530585bf1`, the validation
partition, and the same exact per-seed cache protocol as ALS. The second
command is required before making any comparison claim against the full ALS
result.
