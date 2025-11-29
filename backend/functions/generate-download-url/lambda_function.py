import json
import boto3
import os
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

s3_client = boto3.client('s3')


@tracer.capture_method
def generate_download_url(bucket: str, key: str, filename: str = None, expiration: int = 3600) -> str:
    """Generate a presigned URL for downloading a file from S3"""
    params = {
        'Bucket': bucket,
        'Key': key
    }

    # Add Content-Disposition header to force download with specific filename
    if filename:
        params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'

    return s3_client.generate_presigned_url(
        'get_object',
        Params=params,
        ExpiresIn=expiration
    )


@tracer.capture_method
def check_file_exists(bucket: str, key: str) -> bool:
    """Check if a file exists in S3"""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    """
    Generate a presigned URL for downloading a file from S3
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        s3_key = body.get('key')

        if not s3_key:
            metrics.add_metric(name="ValidationErrors", unit=MetricUnit.Count, value=1)
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': 'true'
                },
                'body': json.dumps({
                    'error': 'Missing required parameter: key'
                })
            }

        bucket_name = os.environ['S3_BUCKET']
        filename = body.get('filename')

        logger.info("Generating download URL", extra={"bucket": bucket_name, "key": s3_key})

        # Check if file exists
        if not check_file_exists(bucket_name, s3_key):
            metrics.add_metric(name="FileNotFound", unit=MetricUnit.Count, value=1)
            logger.warning("File not found", extra={"key": s3_key})
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': 'true'
                },
                'body': json.dumps({
                    'error': 'File not found'
                })
            }

        # Generate presigned URL for download
        download_url = generate_download_url(
            bucket=bucket_name,
            key=s3_key,
            filename=filename,
            expiration=3600
        )

        metrics.add_metric(name="DownloadUrlsGenerated", unit=MetricUnit.Count, value=1)
        logger.info("Download URL generated successfully")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'downloadUrl': download_url,
                'key': s3_key,
                'expiresIn': 3600
            })
        }

    except Exception as e:
        logger.exception("Error generating download URL")
        metrics.add_metric(name="Errors", unit=MetricUnit.Count, value=1)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
