import time

from application.recommendation_sessions import RecommendationSessionStore


def test_recommendation_session_expires_after_ttl():
    sessions = RecommendationSessionStore(ttl_seconds=0.01)
    session_id = sessions.create([(20, 0.9), (30, 0.8)])

    assert sessions.get(session_id) == [(20, 0.9), (30, 0.8)]

    time.sleep(0.02)

    assert sessions.get(session_id) is None


def test_recommendation_session_cache_is_bounded():
    sessions = RecommendationSessionStore(max_sessions=1)
    first = sessions.create([(20, 0.9)])
    second = sessions.create([(30, 0.8)])

    assert sessions.get(first) is None
    assert sessions.get(second) == [(30, 0.8)]
