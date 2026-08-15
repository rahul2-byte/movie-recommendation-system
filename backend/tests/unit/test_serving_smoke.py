import pytest
from serving.serving_smoke_test import validate_recommendation_response


def test_smoke_response_validator_rejects_seed_and_duplicate_results():
    with pytest.raises(ValueError, match="seed"):
        validate_recommendation_response(
            {"recommendations": [{"tmdbId": 603, "title": "Seed"}]},
            seed_tmdb_ids=[603],
            limit=10,
        )

    with pytest.raises(ValueError, match="duplicate"):
        validate_recommendation_response(
            {
                "recommendations": [
                    {"tmdbId": 680, "title": "A"},
                    {"tmdbId": 680, "title": "B"},
                ]
            },
            seed_tmdb_ids=[603],
            limit=10,
        )
