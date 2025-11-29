import json
import boto3
import os
from botocore.config import Config
from typing import Dict, Any

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize S3 client at module level (reused across invocations)
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))


@tracer.capture_method
def generate_presigned_url(bucket: str, key: str, expiration: int = 3600) -> str:
    """
    Generate a presigned URL for uploading a file to S3
    """
    url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': bucket,
            'Key': key
        },
        ExpiresIn=expiration
    )
    return url


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler to generate presigned URLs for S3 uploads
    """
    # Handle OPTIONS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({})
        }

    try:
        # Get configuration from environment variables
        bucket = os.environ.get('S3_BUCKET')
        upload_prefix = os.environ.get('UPLOAD_PREFIX', 'uploads/')

        if not bucket:
            raise ValueError("S3_BUCKET environment variable not set")

        # Get the filename from the request
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        logger.info("Processing upload URL request", extra={"file_name": filename})

        if not filename:
            metrics.add_metric(name="ValidationErrors", unit=MetricUnit.Count, value=1)
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Credentials': 'true'
                },
                'body': json.dumps({'error': 'Filename is required'})
            }

        # Generate the key for the file using configured prefix
        key = f"{upload_prefix}{filename}"
        logger.info("Generating presigned URL", extra={"bucket": bucket, "key": key})

        # Generate the presigned URL
        presigned_url = generate_presigned_url(
            bucket=bucket,
            key=key
        )

        metrics.add_metric(name="PresignedUrlsGenerated", unit=MetricUnit.Count, value=1)
        logger.info("Presigned URL generated successfully")

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'key': key
            })
        }

    except Exception as e:
        logger.exception("Error generating presigned URL")
        metrics.add_metric(name="Errors", unit=MetricUnit.Count, value=1)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
