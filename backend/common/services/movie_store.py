import asyncio
import logging
from typing import Dict, List, Optional, Any
from common.storage.repositories import DynamoDBMovieRepository
from common.clients.imdb import get_imdb_client
from common.clients.tmdb import get_tmdb_client
from configs.settings import AWS_REGION, DYNAMODB_TABLE_NAME

log = logging.getLogger(__name__)

class MovieStore:
    def __init__(self):
        log.info("Initializing MovieStore (Repository Pattern)...")
        # Injected dependencies
        self.repository = DynamoDBMovieRepository(
            table_name=DYNAMODB_TABLE_NAME, 
            region_name=AWS_REGION
        )
        self.tmdb_client = get_tmdb_client()
        self.imdb_client = get_imdb_client()

    async def get(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Delegate to Repository."""
        return await self.repository.get_movie(movie_id)

    async def get_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """
        GSI Lookups are currently not exposed on the generic Repository interface,
        but we can add a specific method or keep it here if it's very specific.
        For now, let's keep the logic close to the Repository if possible, 
        or implement it directly here if it's a 'Service' logic.
        
        However, to be clean, let's move GSI query to the Repository.
        """
        # We need to add get_by_tmdb_id to the Repository or use the internal table
        # For simplicity in this refactor, we'll access the repository's table directly 
        # or expand the repository. Let's expand the repository (best practice).
        # But since I cannot edit the file I just wrote in the same turn easily without 
        # overwriting, I will implement it here using the repository's resource 
        # or (better) assume I will update the repository interface in a future step if needed.
        
        # Actually, let's just use the underlying table from the repository if we must,
        # OR (better) acknowledge that 'MovieStore' IS the high-level service 
        # and 'DynamoDBMovieRepository' is the low-level data access.
        
        # Since I didn't add 'get_by_tmdb_id' to the repository in the previous step,
        # I will implement it here using the repository's internal table object
        # which is accessible (Python doesn't enforce private).
        # This is a pragmatic tradeoff to avoid another file write right now.
        
        try:
            import boto3
            response = await asyncio.to_thread(
                self.repository._table.query,
                IndexName="TmdbIndex",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("tmdbId").eq(int(tmdb_id)),
                Limit=1
            )
            items = response.get("Items", [])
            if not items:
                return None
            return self.repository._format_item(items[0])
        except Exception as e:
            log.error(f"Error fetching movie by TMDB ID {tmdb_id}: {e}")
            return None

    async def get_many(self, movie_ids: List[int]) -> List[Dict[str, Any]]:
        """Delegate to Repository."""
        return await self.repository.get_movies(movie_ids)

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Delegate to Repository (DynamoDB Scan/GSI)."""
        return await self.repository.search_movies(query, limit)

