from common import lifecycle


def test_lifecycle_uses_bundle_pipeline_when_bundle_dir_is_configured(monkeypatch):
    created = {}

    class Recommender:
        @classmethod
        def load(cls, path):
            created["bundle_path"] = path
            return "recommender"

    class Pipeline:
        def __init__(self, recommender, movie_store):
            created["recommender"] = recommender
            created["movie_store"] = movie_store

    store = object()
    monkeypatch.setattr(lifecycle, "BundleRecommender", Recommender, raising=False)
    monkeypatch.setattr(
        lifecycle, "BundleRecommendationPipeline", Pipeline, raising=False
    )
    monkeypatch.setattr(lifecycle.settings, "MODEL_BUNDLE_DIR", "/models")
    monkeypatch.setattr(lifecycle, "_movie_store", store)
    monkeypatch.setattr(lifecycle, "_pipeline", None)

    pipeline = lifecycle.get_pipeline()

    assert isinstance(pipeline, Pipeline)
    assert created == {
        "bundle_path": "/models",
        "recommender": "recommender",
        "movie_store": store,
    }
