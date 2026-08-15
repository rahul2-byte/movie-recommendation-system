# Offline Temporal Evaluation Protocol

## Input and relevance

The input is the canonical interaction data prepared within an immutable
`backend/data/versions/<dataset-version>/` directory. MovieLens IDs are lineage
fields only; all recommendation identities are `tmdb_id`.

A positive interaction is a deduplicated latest rating of at least 3.0. A user
is eligible only when they have at least eight positive interactions, six
training interactions, and at least one positive in both validation and test.
This measures recovery of movies rated moderate-or-better; it must not be
described as strictly liked-movie recall.

## Temporal partitions

Each eligible user's own chronological history is partitioned independently:

- train: first 60 percent, with a minimum of six interactions;
- validation: next 20 percent, with a minimum of one interaction;
- test: the remaining interactions, with a minimum of one interaction.

For an eight-interaction history this yields `6 / 1 / 1`; larger histories use
the configured proportions. The builder preserves timestamp order within every
user, so a user's training history cannot include that user's validation or test
interaction. It records the source/config/output hashes in `manifest.json`.

Interactions with the same timestamp are never split across a boundary. Users
without two strict timestamp boundaries are excluded rather than evaluated with
ambiguous event order.

## Query construction

Future training derives rolling five-seed histories from `train.parquet` only.
The next strictly later positive movie is the target; the sampling cap belongs
to the future training configuration, not this split contract.

Validation has one query per eligible user: the five most recent train movies
are seeds and all validation positives are ground truth. Test has one query per
eligible user: the five most recent pre-test movies (train plus validation) are
seeds and all test positives are ground truth.

## Limitations

MovieLens ratings are explicit feedback, not engagement. The enriched metadata
is a static snapshot without historical feature timestamps. Offline quality and
online user impact are **NOT YET MEASURED**.

This is a per-user chronological protocol, not a single global deployment-date
simulation: a later interaction from one user can appear in training while an
earlier interaction from another user is evaluated. A strict global-time split
may be added later as a separate stress benchmark, not mixed with these results.

## Evaluation commands

The evaluation runner reads only the immutable split artifact. By default it
evaluates validation; test requires an explicit final-evaluation flag.

```bash
PYTHONPATH=backend uv run --frozen python -m evaluation.cli popularity --ci
PYTHONPATH=backend uv run --frozen python -m evaluation.cli popularity
PYTHONPATH=backend uv run --frozen python -m evaluation.cli popularity --partition test --final-evaluation
```

Every run writes ignored machine-readable evidence under
`backend/artifacts/evaluation/<run_id>/` and logs a local MLflow run. Existing
retrieval/ranking artifacts are not evaluated as evidence until reproducible
Python training emits their artifact manifests.

## LightGBM ranking protocol

The authoritative ranker command consumes only immutable ranking feature
artifacts. It fits on the inner chronological ranking-train candidates and
uses outer validation candidates only for early stopping and model selection.
The final test partition remains untouched.

Before fitting, the command verifies identical feature schema version, ordered
feature names, feature-config hash, and feature-code hash across train and
validation. It packs Parquet row groups into resumable NumPy memmaps under
`backend/artifacts/ranking_packed/`, avoiding a whole-dataset pandas load.
Packed files are ignored generated artifacts. Ensure the local machine has
several GiB free disk and sufficient RAM for LightGBM's training representation.

```bash
TRAIN_FEATURE_DIR="backend/data/versions/movielens-32m-76a530585bf1/ranking/199cf602b3b0-3a998065a6d6/candidates/48c815591e86/features/762c747d5847"
VALIDATION_FEATURE_DIR="backend/data/versions/movielens-32m-76a530585bf1/ranking/validation/9ca3e740394a/features/0efd3916eb85"

PYTHONPATH=backend uv run --frozen python -m training.ranking.cli \
  --train-feature-dir "$TRAIN_FEATURE_DIR" \
  --validation-feature-dir "$VALIDATION_FEATURE_DIR"
```

Progress is written to stderr and final JSON to stdout. The command writes
`model.txt`, `feature_schema.json`, `validation_metrics.json`, and
`manifest.json` under a versioned model directory, with matching local MLflow
lineage. Validation compares popularity, rank-only Reciprocal Rank Fusion, and
LambdaRank using NDCG@5/10, MAP@10, and MRR@10. Results are **NOT YET
MEASURED** until this command completes successfully.

## Training progress

Every authoritative training command must show terminal progress. Stage-level
work reports only completed stages; evaluation reports completed queries,
elapsed time, and ETA. Progress is written to stderr so the final JSON evidence
on stdout remains machine-readable.

```bash
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli tfidf --ci
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli tfidf
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli als --ci
PYTHONPATH=backend uv run --frozen python -m training.retrieval.cli als
```

Unsupported legacy/native scripts are not authoritative and are excluded until
their Python replacements exist.

TF-IDF evaluation builds an in-memory exact per-seed neighbor cache for the
selected partition before scoring queries. Its bounded FAISS search batch size
is versioned in `configs/evaluation.yaml`; the cache never reads ground-truth
movies and is discarded when the evaluation process exits.
