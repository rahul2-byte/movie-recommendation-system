import boto3
import pandas as pd
import numpy as np
import argparse
import os
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any

import sys

sys.path.append(os.getcwd())

from common.logger import get_logger
from configs.settings import (
    AWS_REGION,
    DYNAMODB_TABLE_NAME,
)

log = get_logger(__name__)


# =====================================================
# Utility Functions
# =====================================================


def convert_float_to_decimal(obj: Any) -> Any:
    if isinstance(obj, float):
        if np.isnan(obj):
            return None
        return Decimal(str(round(obj, 4)))
    if isinstance(obj, dict):
        return {k: convert_float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_float_to_decimal(v) for v in obj]
    return obj


def clean_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if v is not None and v != ""}


def sanitize_item(row: pd.Series) -> Dict[str, Any] | None:
    data = row.to_dict()
    item = {}

    if pd.isna(data.get("movieId")):
        return None

    item["movieId"] = int(data["movieId"])

    if pd.notna(data.get("tmdbId")) and data.get("tmdbId") != -1:
        item["tmdbId"] = int(data["tmdbId"])

    if pd.notna(data.get("title")):
        item["title_lower"] = str(data["title"]).lower()

    for k, v in data.items():
        if k in ["movieId", "tmdbId"]:
            continue

        if pd.isna(v) or v == "":
            continue

        if k in ["vote_count", "release_year", "year"]:
            try:
                item[k] = int(v)
            except Exception:
                continue

        elif isinstance(v, (list, np.ndarray)):
            cleaned = [str(x) for x in v if x]
            if cleaned:
                item[k] = cleaned

        elif isinstance(v, (float, np.floating)):
            item[k] = v

        else:
            item[k] = str(v)

    item = convert_float_to_decimal(item)
    item = clean_item(item)

    return item


# =====================================================
# DynamoDB Setup (Local Safe Version)
# =====================================================


def setup_table(dynamodb, table_name: str):
    client = dynamodb.meta.client

    log.info("Testing DynamoDB connectivity...")
    try:
        client.list_tables()
        log.info("DynamoDB connection OK.")
    except Exception as e:
        log.error(f"Failed to connect to DynamoDB: {e}")
        raise

    existing_tables = client.list_tables().get("TableNames", [])

    if table_name in existing_tables:
        log.info(f"Table {table_name} already exists.")
        return dynamodb.Table(table_name)

    log.info(f"Creating table {table_name} with PAY_PER_REQUEST mode...")

    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "movieId", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "movieId", "AttributeType": "N"},
                {"AttributeName": "tmdbId", "AttributeType": "N"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "TmdbIndex",
                    "KeySchema": [{"AttributeName": "tmdbId", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        log.info("Waiting for table to become ACTIVE...")

        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=table_name, WaiterConfig={"Delay": 1, "MaxAttempts": 20})

        log.info("Table created successfully.")
        return table

    except Exception as e:
        log.error(f"Table creation failed: {e}")
        raise


# =====================================================
# Data Processing
# =====================================================


def process_data() -> pd.DataFrame:
    log.info("Loading Parquet files...")

    base_path = Path("data/processed")

    files = {
        "enriched": base_path / "movies_enriched.parquet",
        "links": base_path / "links.parquet",
        "tags": base_path / "tags.parquet",
        "raw": base_path / "movies.parquet",
    }

    for name, path in files.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

    df_enriched = pd.read_parquet(files["enriched"])
    df_links = pd.read_parquet(files["links"])
    df_tags = pd.read_parquet(files["tags"])
    df_raw = pd.read_parquet(files["raw"])

    log.info("Processing Tags...")
    df_tags = df_tags.dropna(subset=["tag"])
    df_tags["tag"] = df_tags["tag"].astype(str)
    tags_grouped = df_tags.groupby("movieId")["tag"].apply(list).reset_index()
    tags_grouped.rename(columns={"tag": "user_tags"}, inplace=True)

    log.info("Merging Datasets...")
    master = df_raw.merge(df_links, on="movieId", how="left")

    df_enriched = df_enriched.rename(columns={"movie_id": "movieId"})
    master = master.merge(
        df_enriched, on="movieId", how="left", suffixes=("_raw", "_enriched")
    )

    master = master.merge(tags_grouped, on="movieId", how="left")

    master["title"] = master["title_enriched"].fillna(master["title_raw"])
    master["tmdbId"] = master["tmdb_id"].fillna(master["tmdbId"]).fillna(-1).astype(int)

    if "vote_average" in master.columns:
        master["vote_average"] = master["vote_average"].fillna(0.0)

    if "vote_count" in master.columns:
        master["vote_count"] = master["vote_count"].fillna(0)

    output_path = Path("artifacts/native/search_index.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    master.to_parquet(output_path)

    log.info(f"Search Index Saved ({len(master)} records) to {output_path}")
    return master


# =====================================================
# Upload Phase
# =====================================================


def upload_to_dynamodb(
    file_path: str,
    table_name: str,
    region_name: str,
    endpoint_url: str | None = None,
):
    log.info(f"Loading data from {file_path}...")
    df = pd.read_parquet(file_path)

    resource_kwargs = {
        "service_name": "dynamodb",
        "region_name": region_name,
    }
    if endpoint_url:
        resource_kwargs["endpoint_url"] = endpoint_url

    # Use default AWS credential chain (IAM role/profile/env) for production safety.
    dynamodb = boto3.resource(**resource_kwargs)

    table = setup_table(dynamodb, table_name)

    log.info("Uploading to DynamoDB (Batch)...")

    count = 0
    total = len(df)

    with table.batch_writer() as batch:
        for _, row in df.iterrows():
            try:
                item = sanitize_item(row)
                if item:
                    batch.put_item(Item=item)
                    count += 1

                    if count % 100 == 0:
                        log.info(f"Uploaded {count}/{total}...")

            except Exception as e:
                log.error(f"Failed processing movieId={row.get('movieId')}: {e}")

    log.info(f"Upload Complete. {count} items uploaded.")


# =====================================================
# Main
# =====================================================


def main():
    parser = argparse.ArgumentParser(description="Ingest Movie Data to DynamoDB")
    parser.add_argument("--skip-processing", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument(
        "--file-path",
        default="artifacts/native/search_index.parquet",
        help="Parquet file to upload",
    )
    parser.add_argument(
        "--table-name",
        default=os.getenv("DYNAMODB_TABLE_NAME", DYNAMODB_TABLE_NAME),
        help="Target DynamoDB table name",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", AWS_REGION),
        help="AWS region",
    )
    parser.add_argument(
        "--endpoint-url",
        default=os.getenv("AWS_ENDPOINT_URL", "") or None,
        help="Optional DynamoDB endpoint URL (useful for local DynamoDB)",
    )

    args = parser.parse_args()

    if not args.skip_processing:
        log.info("Starting Data Processing Phase...")
        process_data()

    if not args.skip_upload:
        log.info("Starting Upload Phase...")
        upload_to_dynamodb(
            file_path=args.file_path,
            table_name=args.table_name,
            region_name=args.region,
            endpoint_url=args.endpoint_url,
        )


if __name__ == "__main__":
    main()
