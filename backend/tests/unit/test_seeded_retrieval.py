from retrieval.seeded import collect_seed_candidates, order_candidate_ids


def test_collects_each_seed_independently_and_retains_seed_evidence():
    calls: list[int] = []

    def retrieve_one(seed_id: int, top_k: int):
        calls.append(seed_id)
        return [(seed_id * 10, 0.9), (999, 0.8)]

    evidence = collect_seed_candidates(
        [1, 2, 3, 4, 5], retrieve_one=retrieve_one, source="tfidf", top_k=2
    )

    assert calls == [1, 2, 3, 4, 5]
    assert [
        (row.seed_tmdb_id, row.candidate_tmdb_id, row.rank) for row in evidence
    ] == [
        (1, 10, 1),
        (1, 999, 2),
        (2, 20, 1),
        (2, 999, 2),
        (3, 30, 1),
        (3, 999, 2),
        (4, 40, 1),
        (4, 999, 2),
        (5, 50, 1),
        (5, 999, 2),
    ]
    assert order_candidate_ids(evidence) == [999, 10, 20, 30, 40, 50]


def test_skips_invalid_duplicate_and_seed_candidates():
    def retrieve_one(seed_id: int, top_k: int):
        return [(seed_id, 1.0), (0, 0.9), (8, 0.8), (8, 0.7)]

    evidence = collect_seed_candidates(
        [7, 7, 0], retrieve_one=retrieve_one, source="als", top_k=4
    )

    assert [(row.seed_tmdb_id, row.candidate_tmdb_id) for row in evidence] == [(7, 8)]
