"""Minimal terminal progress for authoritative training commands."""

from __future__ import annotations

import sys
import time
from typing import TextIO


class TerminalProgress:
    """Render completed work to stderr without contaminating JSON stdout."""

    def __init__(self, stage: str, total: int, stream: TextIO | None = None) -> None:
        if total < 1:
            raise ValueError("total must be positive")
        self.stage = stage
        self.total = total
        self.stream = stream or sys.stderr
        self.started = time.perf_counter()

    def update(self, completed: int, detail: str = "") -> None:
        completed = min(max(completed, 0), self.total)
        elapsed = time.perf_counter() - self.started
        eta = (elapsed / completed * (self.total - completed)) if completed else 0.0
        percent = completed / self.total * 100
        suffix = f" | {detail}" if detail else ""
        self.stream.write(
            f"\r\033[2K[{self.stage}] {completed}/{self.total} {percent:5.1f}% "
            f"elapsed {elapsed:.1f}s ETA {eta:.1f}s{suffix}"
        )
        if completed == self.total:
            self.stream.write("\n")
        self.stream.flush()
