import abc

from common.types import Query


class BaseRetriever(abc.ABC):
    """Abstract base class for all retrieval algorithms."""

    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> list[tuple[int, float, str]]:
        """
        Retrieves candidate TMDB IDs for a given query.

        Args:
            query: The query object containing seed movie IDs.
            top_k: The number of candidates to retrieve.

        Returns:
            A list of tuples: (tmdb_id, similarity_score, retriever_name).
        """
        pass
