from typing import Dict, List

from .retrievers.base import BaseRetriever


class RetrieverRegistry:
    """
    Central registry controlling:
    - which retrievers are active
    - recall quotas per retriever

    This avoids hardcoding logic inside the orchestrator.
    """

    def __init__(
        self,
        retrievers: List[BaseRetriever],
        quotas: Dict[str, int],
    ) -> None:
        self._retrievers = {r.name: r for r in retrievers}
        self._quotas = quotas

    def active_retrievers(self) -> List[BaseRetriever]:
        """Return active retrievers."""
        return list(self._retrievers.values())

    def quota(self, retriever_name: str) -> int:
        """Recall quota for a retriever."""
        return self._quotas.get(retriever_name, 0)
