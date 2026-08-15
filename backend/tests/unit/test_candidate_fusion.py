import pytest
from serving.candidate_fusion import collect_source_candidates, fuse_reciprocal_ranks


class _Retriever:
    def retrieve_one(self, seed_tmdb_id: int, top_k: int):
        return {
            1: [(10, 0.9), (20, 0.8)],
            2: [(20, 0.9), (30, 0.8)],
        }[seed_tmdb_id][:top_k]


def test_collection_excludes_seeds_and_prioritizes_seed_support():
    assert collect_source_candidates(_Retriever(), [1, 2], 3) == {
        20: 1,
        10: 2,
        30: 3,
    }


def test_rrf_fusion_is_deterministic_and_tie_breaks_by_movie_id():
    ranks = {"als": {10: 1, 20: 2}, "content": {20: 1, 30: 2}}

    fused_candidates = fuse_reciprocal_ranks(ranks, 60, 3)

    assert [movie_id for movie_id, _ in fused_candidates] == [20, 10, 30]
    assert [score for _, score in fused_candidates] == pytest.approx(
        [1 / 61 + 1 / 62, 1 / 61, 1 / 62]
    )
