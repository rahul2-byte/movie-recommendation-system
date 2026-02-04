import abc
from typing import List, Tuple
from common.types import Query

class BaseRetriever(abc.ABC):
    """Abstract base class for all retrieval algorithms."""
    
    def __init__(self, name: str):
        self.name = name
        
    @abc.abstractmethod
    async def retrieve(self, query: Query, top_k: int = 100) -> List[Tuple[int, float, str]]:
        """
        Retrieves candidate movie IDs for a given query.
        
        Args:
            query: The query object containing seed movie IDs.
            top_k: The number of candidates to retrieve.
            
        Returns:
            A list of tuples: (movie_id, similarity_score, retriever_name).
        """
        pass
