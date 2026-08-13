# P1 legacy ranker trainers

Removed the orphaned `train_ranker.py` and `train_ranker_v2.py` scripts. They
implemented obsolete non-temporal/grouped-random training paths and had no
runtime, CI, or supported command consumers. `train_from_csv.py` remains
because the legacy native orchestration still invokes it.

The canonical ranker entrypoint is `python -m training.ranking.cli`.

Verification: focused regression test, full unit suite, Ruff, and diff checks.
