import pytest
from unittest.mock import AsyncMock, MagicMock
from pipeline.pipeline import RecommendationPipeline
from common.types import Query, Candidate

@pytest.mark.asyncio
async def test_pipeline_recommend(movie_store, mock_recall_service, mock_ranker):
    """Test the full pipeline flow: Recall -> Features -> Rank -> Enrich."""
    
    # Mock FeatureBuilder
    feature_builder = MagicMock()
    feature_builder.build_features = MagicMock(return_value=None) # DF mock not needed if ranker is mocked
    
    pipeline = RecommendationPipeline(
        recall_service=mock_recall_service,
        feature_builder=feature_builder,
        ranker=mock_ranker,
        movie_store=movie_store
    )
    
    query = Query(seed_movie_ids=[1])
    results = await pipeline.recommend(query, top_n=2)
    
    # Check that recall was called
    mock_recall_service.recall.assert_called_once()
    
    # Check that ranker was called
    mock_ranker.rank.assert_called_once()
    
    # Check results (we mocked enrichment to return metas if found)
    # IDs 10 and 20 are in mock_recall_service but not in movie_store (which only has 1,2,3)
    # So results might be empty if enrichment fails to find them.
    # Let's adjust mock_recall_service to return valid IDs.
    mock_recall_service.recall.return_value = [
        Candidate(movie_id=2, score=0.9, sources=["s1"]),
        Candidate(movie_id=3, score=0.8, sources=["s2"])
    ]
    
    results = await pipeline.recommend(query, top_n=2)
    assert len(results) == 2
    assert results[0]["movieId"] == 2
    assert "score" in results[0]
    assert "retrieval_sources" in results[0]
