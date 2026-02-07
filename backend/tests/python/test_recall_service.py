import pytest
from unittest.mock import AsyncMock, MagicMock
from retrieval.inference.recall import RecallService
from common.types import Query, Candidate

@pytest.mark.asyncio
async def test_recall_service_merging():
    """Test that multiple retrievers are merged and deduped."""
    service = RecallService()
    
    # Mock retrievers
    r1 = MagicMock()
    r1.retrieve = AsyncMock(return_value=[(10, 0.9, "source1"), (20, 0.5, "source1")])
    
    r2 = MagicMock()
    r2.retrieve = AsyncMock(return_value=[(20, 0.8, "source2"), (30, 0.7, "source2")])
    
    service.retrievers = [r1, r2]
    
    query = Query(seed_movie_ids=[1])
    candidates = await service.recall(query, top_k=10)
    
    # Check deduping (3 unique candidates: 10, 20, 30)
    assert len(candidates) == 3
    
    # Check merging (candidate 20 should have both sources and the max score)
    cand_20 = next(c for c in candidates if c.movie_id == 20)
    assert "source1" in cand_20.sources
    assert "source2" in cand_20.sources
    assert cand_20.score == 0.8 # max(0.5, 0.8)

@pytest.mark.asyncio
async def test_recall_service_seed_exclusion():
    """Test that seed movies are excluded from results."""
    service = RecallService()
    r1 = MagicMock()
    r1.retrieve = AsyncMock(return_value=[(1, 0.9, "source1"), (10, 0.8, "source1")])
    service.retrievers = [r1]
    
    query = Query(seed_movie_ids=[1])
    candidates = await service.recall(query, top_k=10)
    
    # ID 1 should be excluded
    assert len(candidates) == 1
    assert candidates[0].movie_id == 10
