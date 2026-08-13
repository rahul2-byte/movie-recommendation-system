#!/bin/bash
set -e

# Wait for DynamoDB
echo "Waiting for DynamoDB..."
python3 <<END
import boto3
import time
import os
from botocore.exceptions import ClientError

endpoint_url = os.environ.get('AWS_ENDPOINT_URL', 'http://0.0.0.0:8000')
region_name = os.environ.get('AWS_REGION', 'us-east-1')
table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'Movies')

dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name=region_name)

def wait_for_table():
    retries = 30
    while retries > 0:
        try:
            # Just check connection
            list(dynamodb.tables.all())
            
            # Check table
            table = dynamodb.Table(table_name)
            try:
                table.load()
                print(f"Table {table_name} exists.")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print(f"Table {table_name} does not exist. Creating...")
                    dynamodb.create_table(
                        TableName=table_name,
                        KeySchema=[{'AttributeName': 'movieId', 'KeyType': 'HASH'}],
                        AttributeDefinitions=[
                            {'AttributeName': 'movieId', 'AttributeType': 'N'},
                            {'AttributeName': 'tmdbId', 'AttributeType': 'N'}
                        ],
                        GlobalSecondaryIndexes=[{
                            'IndexName': 'TmdbIndex',
                            'KeySchema': [{'AttributeName': 'tmdbId', 'KeyType': 'HASH'}],
                            'Projection': {'ProjectionType': 'ALL'},
                            'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                        }],
                        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    )
                    print("Table created.")
                    # Wait for creation
                    time.sleep(5)
                    return True
                else:
                    raise e
        except Exception as e:
             print(f"Connection attempt failed: {e}")
        
        time.sleep(2)
        retries -= 1
    return False

if wait_for_table():
    print("DynamoDB is ready.")
else:
    print("Failed to connect to or setup DynamoDB.")
    exit(1)
END

# Check if data needs ingestion (optional)
# Start the application
echo "Starting FastAPI server..."
# Use uvicorn directly.
# --reload is useful for local dev if volumes are mounted
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
