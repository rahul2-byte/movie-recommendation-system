"""Dependency-free smoke check for a running recommendation API."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from typing import Any
from urllib.request import Request, urlopen


def validate_recommendation_response(
    payload: dict[str, Any], *, seed_tmdb_ids: list[int], limit: int
) -> int:
    """Validate recommendation count, uniqueness, and seed exclusion."""
    recommendations = payload.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        raise ValueError("response has no recommendations")
    if len(recommendations) > limit:
        raise ValueError("response exceeds requested limit")

    seen = set(seed_tmdb_ids)
    for movie in recommendations:
        tmdb_id = movie.get("tmdbId") if isinstance(movie, dict) else None
        if not isinstance(tmdb_id, int) or tmdb_id <= 0:
            raise ValueError("response has an invalid TMDB ID")
        if tmdb_id in seed_tmdb_ids:
            raise ValueError("response contains a seed movie")
        if tmdb_id in seen:
            raise ValueError("response contains a duplicate movie")
        seen.add(tmdb_id)
    return len(recommendations)


def main() -> None:
    """Exercise the local recommendation endpoint with deterministic seeds."""
    parser = ArgumentParser(description="Smoke-test a running recommendation API.")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--seed-tmdb-ids", type=int, nargs="+", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()
    if not 1 <= len(args.seed_tmdb_ids) <= 5:
        parser.error("--seed-tmdb-ids requires between one and five IDs")
    if args.limit < 1:
        parser.error("--limit must be positive")

    request = Request(
        f"{args.base_url.rstrip('/')}/api/v1/recommend",
        data=json.dumps(
            {"seed_tmdb_ids": args.seed_tmdb_ids, "limit": args.limit}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=args.timeout_seconds) as response:  # noqa: S310
        payload = json.load(response)
    count = validate_recommendation_response(
        payload, seed_tmdb_ids=args.seed_tmdb_ids, limit=args.limit
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "base_url": args.base_url.rstrip("/"),
                "seed_tmdb_ids": args.seed_tmdb_ids,
                "recommendation_count": count,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
