import asyncio
from typing import Dict, List, Tuple

from common.logger import get_logger
from common.types import Candidate, Query

from retrieval.inference.base_retriever import BaseRetriever
from retrieval.models.als import ALSRetriever
from retrieval.models.content_based import ContentBasedRetriever
from retrieval.models.tfidf import TfidfRetriever
from retrieval.models.two_tower import TwoTowerRetriever

log = get_logger(__name__)


class RecallService:
    def __init__(self):
        self.retrievers: List[BaseRetriever] = []
        self._initialized = False
        self._lock = asyncio.Lock()

    async def _ensure_initialized(self):
        if self._initialized:
            return
        async with self._lock:
            if not self._initialized:
                log.info("RecallService: Lazily loading retrievers in parallel...")
                # Parallel initialization of retriever objects (if they support async init)
                # Most just load indices from disk/S3 which is blocking, but we run in thread pool if needed
                # For now, sequential instantiation but within the lock is safe for Lambda.
                self.retrievers = [
                    TfidfRetriever(),
                    ContentBasedRetriever(),
                    ALSRetriever(),
                    TwoTowerRetriever(),
                ]
                self._initialized = True
                log.info(
                    f"RecallService initialized with {len(self.retrievers)} retrievers."
                )

    async def recall(self, query: Query, top_k: int = 500) -> List[Candidate]:
        if not query.seed_movie_ids:
            return []
        await self._ensure_initialized()
        log.info(f"RecallService: Processing query with seeds: {query.seed_movie_ids}")
        results = await asyncio.gather(
            *[r.retrieve(query, top_k=top_k * 2) for r in self.retrievers]
        )
        merged: Dict[int, Candidate] = {}
        for retriever_output in results:
            for mid, score, source in retriever_output:
                if mid in query.seed_movie_ids:
                    continue
                if mid not in merged:
                    merged[mid] = Candidate(movie_id=mid)
                c = merged[mid]
                if source not in c.sources:
                    c.sources.append(source)
                c.scores[source] = score
                c.score = max(c.score, score)
        final = [
            c
            for c in merged.values()
            if c.movie_id not in query.seed_movie_ids and c.movie_id != 0
        ]
        final.sort(key=lambda c: c.score, reverse=True)
        return final[:top_k]
