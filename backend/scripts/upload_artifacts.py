#!/usr/bin/env python3
import os
import sys
import json
import time
import hashlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Configuration
DEFAULT_BUCKET_NAME = "movie-recommendation-artifacts"
ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts" / "models"
REGION_NAME = os.getenv("AWS_REGION", "ap-south-1")

logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

def get_git_info():
    try:
        commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode("utf-8")
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip().decode("utf-8")
        return commit_hash, branch
    except Exception as e:
        logger.warning(f"Could not retrieve git info: {e}")
        return "unknown", "unknown"

def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def upload_file(s3_client, bucket, local_path, s3_key):
    try:
        s3_client.upload_file(str(local_path), bucket, s3_key)
        logger.info(f"Uploaded: {local_path.name} -> s3://{bucket}/{s3_key}")
        return True
    except ClientError as e:
        logger.error(f"Failed to upload {local_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Upload model artifacts to AWS S3 with versioning.")
    parser.add_argument(
        "--message",
        "-m",
        default="automated-upload",
        help="Description of changes/version",
    )
    parser.add_argument("--bucket", default=DEFAULT_BUCKET_NAME, help="S3 bucket name")
    parser.add_argument("--dry-run", action="store_true", help="Simulate upload without actual transfer")
    
    args = parser.parse_args()
    
    # 1. Validation
    if not ARTIFACTS_DIR.exists():
        logger.error(f"Artifacts directory not found: {ARTIFACTS_DIR}")
        sys.exit(1)

    # Check AWS Credentials
    session = boto3.Session()
    s3 = session.client('s3', region_name=REGION_NAME)
    
    try:
        # Check if bucket exists/accessible
        if not args.dry_run:
            s3.head_bucket(Bucket=args.bucket)
    except (ClientError, NoCredentialsError, Exception) as e:
        logger.warning(f"Could not access bucket '{args.bucket}': {e}")
        logger.warning("Falling back to --dry-run mode.")
        args.dry_run = True

    # 2. Prepare Versioning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    commit_hash, branch = get_git_info()
    version_id = f"{timestamp}_{commit_hash[:7]}"
    s3_prefix = f"artifacts/{version_id}"
    
    logger.info(f"Starting upload process...")
    logger.info(f"Version ID: {version_id}")
    logger.info(f"Bucket: {args.bucket}")
    logger.info(f"Local Dir: {ARTIFACTS_DIR}")
    
    # 3. Scan and Prepare Files
    files_to_upload = []
    file_metadata = {}
    
    # Define essential paths to include
    include_paths = [
        Path("als"),
        Path("content_based"),
        Path("ranker"),
        Path("tfidf"),
        Path("two_tower")
    ]

    for item in ARTIFACTS_DIR.rglob("*"):
        if item.is_file() and not item.name.startswith("."):
            rel_path = item.relative_to(ARTIFACTS_DIR)
            
            # Check if file is in the allowed list
            is_allowed = False
            for allowed in include_paths:
                # Check if rel_path starts with allowed directory OR is the allowed file
                if str(rel_path).startswith(str(allowed)):
                    is_allowed = True
                    break
            
            if not is_allowed:
                continue

            s3_key = f"{s3_prefix}/{rel_path}"
            
            # Calculate checksum
            checksum = calculate_md5(item)
            
            files_to_upload.append((item, s3_key))
            file_metadata[str(rel_path)] = {
                "size_bytes": item.stat().st_size,
                "md5": checksum,
                "s3_key": s3_key
            }

    if not files_to_upload:
        logger.warning("No files found to upload.")
        sys.exit(0)

    # 4. Upload Files
    success_count = 0
    fail_count = 0
    
    for local_path, s3_key in files_to_upload:
        if args.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path.name} to {s3_key}")
            success_count += 1
        else:
            if upload_file(s3, args.bucket, local_path, s3_key):
                success_count += 1
            else:
                fail_count += 1

    # 5. Create and Upload Manifest/Metadata
    manifest = {
        "version_id": version_id,
        "timestamp": datetime.now().isoformat(),
        "git_commit": commit_hash,
        "git_branch": branch,
        "description": args.message,
        "user": os.getenv("USER", "unknown"),
        "files": file_metadata,
        "total_files": len(files_to_upload),
        "status": "partial" if fail_count > 0 else "complete"
    }
    
    manifest_path = ARTIFACTS_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    manifest_s3_key = f"{s3_prefix}/manifest.json"
    
    if args.dry_run:
        logger.info(f"[DRY RUN] Would upload manifest to {manifest_s3_key}")
    elif upload_file(s3, args.bucket, manifest_path, manifest_s3_key):
        logger.info("Manifest uploaded successfully.")
        # Optionally update a 'latest' pointer file
        try:
            s3.put_object(
                Bucket=args.bucket,
                Key="artifacts/latest_version.txt",
                Body=version_id.encode('utf-8')
            )
            logger.info("Updated 'latest' pointer.")
        except Exception as e:
            logger.warning(f"Could not update 'latest' pointer: {e}")
    else:
        logger.error("Failed to upload manifest.")
        
    # Cleanup local manifest
    if manifest_path.exists():
        manifest_path.unlink()

    # 6. Final Report
    logger.info("-" * 50)
    logger.info(f"Upload Summary for Version: {version_id}")
    logger.info(f"Success: {success_count}")
    logger.info(f"Failed:  {fail_count}")
    
    if fail_count == 0:
        logger.success("All artifacts uploaded successfully! 🚀")
        print(f"\n✅ Artifacts available at: s3://{args.bucket}/{s3_prefix}/")
    else:
        logger.error("Some files failed to upload. Check logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
