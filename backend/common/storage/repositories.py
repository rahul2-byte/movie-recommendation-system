import asyncio
import json
import logging
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from configs.settings import (
    AWS_ENDPOINT_URL,
    AWS_REGION,
    DYNAMODB_TABLE_NAME,
    S3_ARTIFACT_BUCKET,
    TMDB_IMAGE_BASE,
    TMDB_POSTER_SIZE,
)

log = logging.getLogger(__name__)


class DynamoDBMovieRepository:
    def __init__(
        self, table_name: str = DYNAMODB_TABLE_NAME, region_name: str = AWS_REGION
    ):
        self.table_name = table_name
        self.region_name = region_name
        endpoint_url = AWS_ENDPOINT_URL or None
        self._dynamodb = boto3.resource(
            "dynamodb", region_name=self.region_name, endpoint_url=endpoint_url
        )
        self._table = self._dynamodb.Table(self.table_name)
        log.info(
            "dynamodb.repo.init table=%s region=%s endpoint=%s",
            self.table_name,
            self.region_name,
            endpoint_url or "aws-default",
        )

    def _decimal_to_float(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, list):
            return [self._decimal_to_float(i) for i in obj]
        if isinstance(obj, dict):
            return {k: self._decimal_to_float(v) for k, v in obj.items()}
        return obj

    def _format_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Convert DynamoDB item to API response format."""
        item = self._decimal_to_float(item)
        year_value = item.get("release_year") or item.get("year")
        vote_count = int(item.get("vote_count", 0))

        poster_path = item.get("poster_path")
        backdrop_path = item.get("backdrop_path")

        poster_url = None
        if poster_path:
            poster_url = f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{poster_path}"

        backdrop_url = None
        if backdrop_path:
            backdrop_url = f"{TMDB_IMAGE_BASE}/original{backdrop_path}"

        return {
            "movieId": int(item["movieId"]),
            "tmdbId": int(item["tmdbId"]) if item.get("tmdbId") else None,
            "title": item.get("title", "Unknown"),
            "year": int(year_value) if year_value else None,
            "genres": item.get("genres", []),
            "overview": item.get("overview"),
            "posterUrl": poster_url,
            "backdropUrl": backdrop_url,
            "rating": item.get("vote_average", 0.0),
            "voteCount": vote_count,
            "vote_count": vote_count,
            "imdb_rating": item.get("imdb_rating"),
            "imdb_votes": (
                int(item.get("imdb_votes", 0))
                if item.get("imdb_votes") is not None
                else 0
            ),
            "keywords": item.get("keywords", []),
            "user_tags": item.get("user_tags", []),
            "runtime_minutes": item.get("runtime_minutes", 0),
            "release_year": int(year_value) if year_value else None,
        }

    async def get_movie(self, movie_id: int) -> dict[str, Any] | None:
        try:
            response = await asyncio.to_thread(
                self._table.get_item, Key={"movieId": int(movie_id)}
            )
            item = response.get("Item")
            return self._format_item(item) if item else None
        except ClientError as e:
            log.exception("dynamodb.get_movie.failed movie_id=%s error=%s", movie_id, e)
            return None

    async def get_movies(self, movie_ids: list[int]) -> list[dict[str, Any]]:
        if not movie_ids:
            return []

        unique_ids = list(set(movie_ids))
        results = []
        chunk_size = 100

        for i in range(0, len(unique_ids), chunk_size):
            chunk = unique_ids[i : i + chunk_size]
            keys = [{"movieId": int(mid)} for mid in chunk]
            try:
                response = await asyncio.to_thread(
                    self._dynamodb.batch_get_item,
                    RequestItems={
                        self.table_name: {
                            "Keys": keys,
                            "ProjectionExpression": "movieId, tmdbId, title, overview, poster_path, backdrop_path, release_year, vote_average, vote_count, imdb_rating, imdb_votes, genres, user_tags, keywords, runtime_minutes, popularity_score",
                        }
                    },
                )
                items = response.get("Responses", {}).get(self.table_name, [])
                results.extend([self._format_item(item) for item in items])
            except Exception as e:
                log.exception(
                    "dynamodb.get_movies.failed chunk_start=%s chunk_size=%s error=%s",
                    i,
                    len(chunk),
                    e,
                )

        return results

    async def search_movies(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Naive search using FilterExpression (Scan) or GSI if available.
        """
        if not query or len(query) < 2:
            return []

        query_lower = query.lower()

        try:
            results = []
            scan_kwargs = {
                "FilterExpression": boto3.dynamodb.conditions.Attr(
                    "title_lower"
                ).contains(query_lower),
                "ProjectionExpression": "movieId, tmdbId, title, overview, poster_path, release_year",
            }

            done = False
            start_key = None
            scanned_count = 0
            MAX_SCAN = 100000  # Scan up to 100k items (full table) to find matches

            while not done:
                if start_key:
                    scan_kwargs["ExclusiveStartKey"] = start_key

                # Run sync scan in thread
                response = await asyncio.to_thread(self._table.scan, **scan_kwargs)

                items = response.get("Items", [])
                scanned_count += response.get("ScannedCount", 0)

                results.extend([self._format_item(item) for item in items])

                start_key = response.get("LastEvaluatedKey", None)

                # Stop if we have enough results, or no more items, or exceeded safety limit
                if (
                    len(results) >= limit
                    or start_key is None
                    or scanned_count > MAX_SCAN
                ):
                    done = True

            return results[:limit]

        except Exception as e:
            log.exception(
                "dynamodb.search.failed query=%s limit=%s error=%s", query, limit, e
            )
            return []


class S3ArtifactRepository:
    def __init__(
        self, bucket_name: str = S3_ARTIFACT_BUCKET, region_name: str = AWS_REGION
    ):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3", region_name=region_name)
        # Ephemeral cache directory
        self.cache_dir = Path("/tmp/movie_artifacts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        log.info(
            "s3.repo.init bucket=%s region=%s cache_dir=%s",
            self.bucket_name,
            region_name,
            self.cache_dir,
        )

    def download_artifact(self, key: str, force: bool = False) -> Path:
        """
        Downloads an artifact from S3 to local cache.
        Returns the local path.
        """
        local_path = self.cache_dir / key
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Development Fallback: Check local artifacts first
        # This allows running locally without S3 access
        dev_local_source = Path("/app/artifacts") / key
        if dev_local_source.exists():
            log.info(f"Found local artifact override: {dev_local_source}")
            if not local_path.exists() or force:
                shutil.copy2(dev_local_source, local_path)
            return local_path

        if local_path.exists() and not force:
            log.info(f"Artifact {key} found in cache.")
            return local_path

        log.info(f"Downloading artifact {key} from S3...")
        try:
            self.s3_client.download_file(self.bucket_name, key, str(local_path))
            return local_path
        except ClientError as e:
            log.exception(
                "s3.download.failed key=%s bucket=%s error=%s", key, self.bucket_name, e
            )
            raise FileNotFoundError(
                f"Artifact {key} not found in bucket {self.bucket_name}"
            ) from e

    def load_json_artifact(self, key: str) -> dict:
        local_path = self.download_artifact(key)
        with open(local_path) as f:
            return json.load(f)

    def get_artifact_path(self, key: str) -> str:
        """Ensures artifact is present and returns its path."""
        return str(self.download_artifact(key))
