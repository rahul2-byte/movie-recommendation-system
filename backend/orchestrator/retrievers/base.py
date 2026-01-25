from abc import ABC, abstractmethod
from typing import List, Tuple


class BaseRetriever(ABC):
    """
    Abstract interface all retrievers must implement.

    This guarantees orchestrator compatibility.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique retriever name (e.g. 'als', 'two_tower')."""
        raise NotImplementedError

    @abstractmethod
    def retrieve(
        self,
        user_id: int,
        top_k: int,
    ) -> List[Tuple[int, float]]:
        """
        Retrieve candidates for a user.

        Returns:
            List of (item_id, raw_score)
        """
        raise NotImplementedError
