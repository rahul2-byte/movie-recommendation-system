import math
from datetime import datetime
from typing import Optional


def freshness_score(
    release_ts: Optional[int],
    now_ts: Optional[int],
    half_life_days: int,
) -> float:
    """
    Exponential decay freshness score in [0, 1]
    """
    if release_ts is None or now_ts is None:
        return 0.0

    age_days = (now_ts - release_ts) / 86400.0
    if age_days < 0:
        return 1.0

    return math.exp(-math.log(2) * age_days / half_life_days)
