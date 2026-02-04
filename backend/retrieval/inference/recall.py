import asyncio
from typing import List, Dict, Tuple
from common.types import Query, Candidate
from common.logger import get_logger

# Import specific retriever implementations
from retrieval.models.tfidf import TfidfRetriever
from retrieval.models.content_based import ContentBasedRetriever
from retrieval.models.als import ALSRetriever
from retrieval.models.two_tower import TwoTowerRetriever
from retrieval.inference.base_retriever import BaseRetriever

log = get_logger(__name__)

class RecallService:
    def __init__(self):
        """
        Initializes the RecallService by loading all configured retrievers.
        """
        log.info("Initializing RecallService: Loading all active retrievers...")
        self.retrievers: List[BaseRetriever] = []
        
        # Instantiate each retriever
        # For production, these could be loaded dynamically based on config
        self.retrievers.append(TfidfRetriever())
        self.retrievers.append(ContentBasedRetriever())
        self.retrievers.append(ALSRetriever())
        self.retrievers.append(TwoTowerRetriever())
        
        log.info(f"RecallService initialized with {len(self.retrievers)} retrievers.")

    async def recall(self, query: Query, top_k: int = 500) -> List[Candidate]:
        """
        Executes all active retrievers in parallel, merges results, and dedupes.
        
        Args:
            query: The query object containing seed movie IDs.
            top_k: The total number of candidates to retrieve after merging.
            
        Returns:
            A list of unique Candidate objects, enriched with sources and scores.
        """
        if not query.seed_movie_ids:
            return []

        log.info(f"RecallService: Processing query with seeds: {query.seed_movie_ids}")
        
        # Run retrievers in parallel
        # Each retriever returns List[Tuple[int, float, str]] (movie_id, score, source_name)
        # We ask for more candidates from each retriever than the final top_k
        results_from_retrievers = await asyncio.gather(
            *[r.retrieve(query, top_k=top_k * 2) for r in self.retrievers] 
        )

        merged_candidates_map: Dict[int, Candidate] = {}
        
        # Initialize map with seed movies to ensure they are excluded from results
        for seed_id in query.seed_movie_ids:
            # Create a placeholder candidate or simply track the ID for exclusion
            merged_candidates_map[seed_id] = Candidate(movie_id=seed_id, sources=["seed_query"])

        for retriever_output in results_from_retrievers:
            for movie_id, score, source_name in retriever_output:
                # Only add if not a seed movie
                if movie_id in query.seed_movie_ids:
                    continue

                if movie_id not in merged_candidates_map:
                    candidate = Candidate(movie_id=movie_id)
                    merged_candidates_map[movie_id] = candidate
                else:
                    candidate = merged_candidates_map[movie_id]

                # Update candidate with source information
                if source_name not in candidate.sources:
                    candidate.sources.append(source_name)
                candidate.scores[source_name] = score # Store individual score
                
                # A simple way to combine retrieval scores (e.g., max score across retrievers)
                candidate.score = max(candidate.score, score) # Take max score across retrievers

        # Filter out seed movies (already handled in loop, but double check) and sort the unique candidates
        final_candidates = [
            c for c in merged_candidates_map.values()
            if c.movie_id not in query.seed_movie_ids and c.movie_id != 0 # movie_id 0 can appear from errors
        ]
        
        # Sort by the combined score (descending)
        final_candidates.sort(key=lambda c: c.score, reverse=True)
        
        log.info(f"RecallService: Generated {len(final_candidates)} unique candidates.")
        return final_candidates[:top_k] # Cap the total candidates before returning
