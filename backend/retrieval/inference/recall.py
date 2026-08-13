import asyncio
import time

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
        self.retrievers: list[BaseRetriever] = []
        self._initialized = False
        self._lock = asyncio.Lock()

    async def _ensure_initialized(self):
        if self._initialized:
            return
        async with self._lock:
            if not self._initialized:
                start = time.perf_counter()
                log.info("recall.init.start")
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
                    "recall.init.success retriever_count={} duration_ms={}",
                    len(self.retrievers),
                    int((time.perf_counter() - start) * 1000),
                )

    async def _safe_retrieve(
        self, retriever: BaseRetriever, query: Query, top_k: int, request_id: str
    ):
        start = time.perf_counter()
        try:
            output = await retriever.retrieve(query, top_k=top_k * 2)
            log.info(
                "recall.retriever.success request_id={} retriever={} candidates={} duration_ms={}",
                request_id,
                retriever.name,
                len(output),
                int((time.perf_counter() - start) * 1000),
            )
            return output
        except Exception:
            log.exception(
                "recall.retriever.failed request_id={} retriever={} duration_ms={}",
                request_id,
                retriever.name,
                int((time.perf_counter() - start) * 1000),
            )
            return []

    async def recall(
        self, query: Query, top_k: int = 500, request_id: str = "n/a"
    ) -> list[Candidate]:
        if not query.seed_tmdb_ids:
            return []
        await self._ensure_initialized()
        total_start = time.perf_counter()
        log.info(
            "recall.start request_id={} top_k={} seeds={}",
            request_id,
            top_k,
            query.seed_tmdb_ids,
        )
        results = await asyncio.gather(
            *[
                self._safe_retrieve(r, query, top_k=top_k, request_id=request_id)
                for r in self.retrievers
            ]
        )
        merged: dict[int, Candidate] = {}
        for retriever_output in results:
            for tmdb_id, score, source in retriever_output:
                if tmdb_id in query.seed_tmdb_ids:
                    continue
                if tmdb_id not in merged:
                    merged[tmdb_id] = Candidate(tmdb_id=tmdb_id)
                c = merged[tmdb_id]
                if source not in c.sources:
                    c.sources.append(source)
                c.scores[source] = score
                c.score = max(c.score, score)
        final = [
            c
            for c in merged.values()
            if c.tmdb_id not in query.seed_tmdb_ids and c.tmdb_id != 0
        ]
        final.sort(key=lambda c: c.score, reverse=True)
        log.info(
            "recall.success request_id={} merged_candidates={} returned={} duration_ms={}",
            request_id,
            len(final),
            min(len(final), top_k),
            int((time.perf_counter() - total_start) * 1000),
        )
        return final[:top_k]
