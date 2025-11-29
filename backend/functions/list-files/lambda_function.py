import json
import boto3
import os

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

s3_client = boto3.client('s3')


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    bucket_name = os.environ['S3_BUCKET']
    processed_prefix = os.environ['PROCESSED_PREFIX']
    rejected_prefix = os.environ['REJECTED_PREFIX']

    # Get query parameter for filtering (processed, rejected, or all)
    query_params = event.get('queryStringParameters') or {}
    status_filter = query_params.get('status', 'all')

    logger.info("Listing files", extra={"status_filter": status_filter})

    files = []

    try:
        # List processed files if requested
        if status_filter in ['all', 'processed']:
            processed_files = list_files_in_prefix(
                bucket_name,
                processed_prefix,
                'processed'
            )
            files.extend(processed_files)

        # List rejected files if requested
        if status_filter in ['all', 'rejected']:
            rejected_files = list_files_in_prefix(
                bucket_name,
                rejected_prefix,
                'rejected'
            )
            # For rejected files, try to fetch error details
            for file in rejected_files:
                if not file['key'].endswith('.error.json'):
                    error_key = file['key'].replace('.json', '.error.json')
                    error_details = get_error_details(bucket_name, error_key)
                    if error_details:
                        file['error'] = error_details

            files.extend(rejected_files)

        # Sort by last modified (newest first)
        files.sort(key=lambda x: x['last_modified'], reverse=True)

        metrics.add_metric(name="FilesListed", unit=MetricUnit.Count, value=len(files))
        logger.info("Files listed successfully", extra={"count": len(files)})

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': os.environ.get('FRONTEND_ORIGIN', '*'),
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'files': files,
                'count': len(files)
            })
        }

    except Exception as e:
        logger.exception("Error listing files")
        metrics.add_metric(name="Errors", unit=MetricUnit.Count, value=1)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': os.environ.get('FRONTEND_ORIGIN', '*')
            },
            'body': json.dumps({
                'error': 'Failed to list files',
                'message': str(e)
            })
        }


@tracer.capture_method
def parse_hive_path(key, prefix):
    """
    Parse Hive-style path to extract partition info.
    Example: processed/year=2025/month=01/day=15/store_id=0001/part-00000.parquet
    Returns dict with year, month, day, store_id or None if not a Hive path.
    """
    # Remove prefix and get the path components
    relative_path = key[len(prefix):] if key.startswith(prefix) else key
    parts = relative_path.split('/')

    partitions = {}
    for part in parts:
        if '=' in part:
            k, v = part.split('=', 1)
            partitions[k] = v

    return partitions if partitions else None


def get_display_name(key, prefix, status):
    """
    Generate a user-friendly display name for the file.
    For Hive-partitioned processed files: store_0001_2025-01-15.parquet
    For rejected files: just the filename
    """
    if status == 'processed':
        partitions = parse_hive_path(key, prefix)
        if partitions and all(k in partitions for k in ['year', 'month', 'day', 'store_id']):
            return f"store_{partitions['store_id']}_{partitions['year']}-{partitions['month']}-{partitions['day']}.parquet"

    # Fallback: just the filename
    return key.split('/')[-1]


@tracer.capture_method
def list_files_in_prefix(bucket_name, prefix, status):
    """List all files in a given S3 prefix"""
    files = []

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                # Skip the prefix itself if it's listed as an object
                if obj['Key'] == prefix:
                    continue

                # For rejected files, skip .error.json files (we'll fetch them separately)
                if status == 'rejected' and obj['Key'].endswith('.error.json'):
                    continue

                # Get partition info for processed files
                partitions = None
                if status == 'processed':
                    partitions = parse_hive_path(obj['Key'], prefix)

                files.append({
                    'key': obj['Key'],
                    'name': get_display_name(obj['Key'], prefix, status),
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'status': status,
                    'partitions': partitions  # Include partition info for frontend
                })

    except Exception as e:
        logger.error("Error listing files in prefix", extra={"prefix": prefix, "error": str(e)})

    return files


@tracer.capture_method
def get_error_details(bucket_name, error_key):
    """Fetch error details from .error.json file"""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=error_key)
        error_data = json.loads(response['Body'].read().decode('utf-8'))
        return error_data.get('error', 'Unknown error')
    except Exception as e:
        logger.debug("Could not fetch error details", extra={"error_key": error_key})
        return None
