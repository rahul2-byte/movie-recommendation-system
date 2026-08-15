import lightgbm as lgb
import numpy as np
from serving.bundle_recommender import BundleRecommender


class _Retriever:
    def __init__(self, rows):
        self.rows = rows

    def retrieve_one(self, seed_tmdb_id, top_k):
        return self.rows.get(seed_tmdb_id, [])[:top_k]


class _Bundle:
    def __init__(self, retrievers, item_graph):
        self.vector_retrievers = retrievers
        self.item_graph = item_graph

    def vector_retriever(self, name):
        return self.vector_retrievers[name]


def _ranker(feature_count: int) -> lgb.Booster:
    features = np.array(
        [[1.0] * feature_count, [0.0] * feature_count, [0.5] * feature_count],
        dtype=np.float32,
    )
    return lgb.train(
        {"objective": "lambdarank", "verbosity": -1, "min_data_in_leaf": 1},
        lgb.Dataset(features, label=[1, 0, 0], group=[3]),
        num_boost_round=2,
    )


def test_bundle_recommender_excludes_seeds_and_uses_all_retrievers():
    feature_names = (
        "retrieval_source_count",
        "retrieval_als_rank",
        "retrieval_als_score_normalized",
        "retrieval_item_graph_rank",
        "retrieval_item_graph_score_normalized",
        "retrieval_two_tower_rank",
        "retrieval_two_tower_score_normalized",
        "retrieval_content_rank",
        "retrieval_content_score_normalized",
        "candidate_train_interaction_count",
        "candidate_train_log_interaction_count",
    )
    rows = {1: [(1, 1.0), (20, 0.9), (30, 0.8)]}
    bundle = _Bundle(
        {name: _Retriever(rows) for name in ("als", "two_tower", "content")},
        _Retriever({1: [(20, 1.0), (40, 0.5)]}),
    )
    recommender = BundleRecommender(
        bundle=bundle,
        model=_ranker(len(feature_names)),
        feature_names=feature_names,
        popularity_counts={20: 9.0, 30: 2.0, 40: 1.0},
        candidate_limit=3,
        rank_constant=60,
    )

    results = recommender.recommend([1], {}, top_n=3)

    assert [item_id for item_id, _ in results] == sorted(
        {item_id for item_id, _ in results}
    ) or len({item_id for item_id, _ in results}) == len(results)
    assert 1 not in {item_id for item_id, _ in results}
    assert {item_id for item_id, _ in results} == {20, 30, 40}


def test_bundle_recommender_uses_content_for_an_unseen_tmdb_seed():
    class Index:
        ntotal = 2

        @staticmethod
        def search(vector, top_k):
            return (
                np.array([[0.9, 0.8]], dtype=np.float32),
                np.array([[0, 1]], dtype=np.int64),
            )

    class ContentRetriever:
        position_by_tmdb_id = {}
        index = Index()
        tmdb_ids = np.array([20, 30], dtype=np.int64)

        def retrieve_one(self, seed_tmdb_id, top_k):
            return []

    class Vectorizer:
        @staticmethod
        def transform(documents):
            assert documents == ["New Movie"]
            return documents

    class SVD:
        @staticmethod
        def transform(documents):
            return np.array([[1.0, 0.0]], dtype=np.float32)

    feature_names = ("retrieval_content_rank",)
    bundle = _Bundle(
        {
            "als": _Retriever({}),
            "two_tower": _Retriever({}),
            "content": ContentRetriever(),
        },
        _Retriever({}),
    )
    recommender = BundleRecommender(
        bundle=bundle,
        model=_ranker(len(feature_names)),
        feature_names=feature_names,
        popularity_counts={},
        candidate_limit=2,
        rank_constant=60,
        content_vectorizer=Vectorizer(),
        content_svd=SVD(),
        content_fields=("title",),
        content_weights={"title": 1},
    )

    results = recommender.recommend([999], {999: {"title": "New Movie"}}, top_n=2)

    assert [item_id for item_id, _ in results] == [20, 30]
