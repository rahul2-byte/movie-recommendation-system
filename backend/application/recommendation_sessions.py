"""Short-lived ranked recommendation sessions for progressive loading."""

from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4


@dataclass(frozen=True)
class RecommendationSession:
    candidates: tuple[tuple[int, float], ...]
    expires_at: float


class RecommendationSessionStore:
    """Keep rank results briefly so scrolling does not rerun the model."""

    def __init__(self, ttl_seconds: int = 900, max_sessions: int = 256):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: OrderedDict[str, RecommendationSession] = OrderedDict()

    def create(self, candidates: list[tuple[int, float]]) -> str:
        self._prune()
        session_id = uuid4().hex
        self._sessions[session_id] = RecommendationSession(
            candidates=tuple(candidates),
            expires_at=monotonic() + self.ttl_seconds,
        )
        while len(self._sessions) > self.max_sessions:
            self._sessions.popitem(last=False)
        return session_id

    def get(self, session_id: str) -> list[tuple[int, float]] | None:
        self._prune()
        session = self._sessions.get(session_id)
        if session is None:
            return None
        self._sessions.move_to_end(session_id)
        return list(session.candidates)

    def _prune(self) -> None:
        now = monotonic()
        for session_id in [
            key for key, session in self._sessions.items() if session.expires_at <= now
        ]:
            self._sessions.pop(session_id, None)
