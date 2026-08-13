"""Low-noise structured progress logging for long ETL stages."""

from __future__ import annotations

import logging
import time


class ProgressReporter:
    def __init__(self, stage: str, total: int | None):
        self.stage = stage
        self.total = total
        self.started_at = time.monotonic()
        self.log = logging.getLogger(__name__)

    def report(self, completed: int, *, rows: int = 0) -> None:
        elapsed = max(time.monotonic() - self.started_at, 0.001)
        rate = completed / elapsed
        remaining = (self.total - completed) / rate if self.total and rate else None
        self.log.info(
            "etl.progress stage=%s completed=%s total=%s percent=%s rows=%s elapsed_s=%.1f eta_s=%s",
            self.stage,
            completed,
            self.total,
            f"{100 * completed / self.total:.1f}" if self.total else "unknown",
            rows,
            elapsed,
            f"{remaining:.1f}" if remaining is not None else "unknown",
        )
