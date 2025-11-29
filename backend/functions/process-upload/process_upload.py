import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json
import os
import re
from decimal import Decimal
from jsonschema import validate, ValidationError, SchemaError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize S3 client at module level (reused across invocations)
s3 = boto3.client('s3')

# Load schema once at module level (cached across invocations)
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'upload-schema.json')
with open(SCHEMA_PATH, 'r') as f:
    UPLOAD_SCHEMA = json.load(f)

# Filename pattern: store_XXXX_YYYY-MM-DD.json
FILENAME_PATTERN = re.compile(r'^store_(\d{4})_(\d{4})-(\d{2})-(\d{2})\.json$')

# PyArrow schema for output Parquet (portable, not AWS-specific)
PARQUET_SCHEMA = pa.schema([
    ("transaction_id", pa.string()),
    ("transaction_timestamp", pa.timestamp("ms")),
    ("item_sku", pa.string()),
    ("item_name", pa.string()),
    ("quantity", pa.int32()),
    ("unit_price", pa.decimal128(10, 2)),
    ("line_total", pa.decimal128(10, 2)),
    ("discount_amount", pa.decimal128(10, 2)),
    ("payment_method", pa.string()),
    ("customer_id", pa.string()),
])


@tracer.capture_method
def parse_filename(filename):
    """
    Parse filename to extract store_id and date components.
    Expected format: store_XXXX_YYYY-MM-DD.json
    Returns (store_id, year, month, day) or (None, None, None, None) if invalid.
    """
    match = FILENAME_PATTERN.match(filename)
    if not match:
        return None, None, None, None

    store_id, year, month, day = match.groups()
    return store_id, year, month, day


@tracer.capture_method
def validate_json_schema(data):
    """
    Validate JSON data against the upload schema.
    Returns (is_valid, error_message)
    """
    try:
        validate(instance=data, schema=UPLOAD_SCHEMA)
        return True, None
    except ValidationError as e:
        error_msg = f"Validation failed: {e.message} at path: {'.'.join(str(p) for p in e.path)}"
        return False, error_msg
    except SchemaError as e:
        error_msg = f"Schema error: {e.message}"
        return False, error_msg


@tracer.capture_method
def reject_file(s3, bucket_name, object_key, rejected_prefix, error_message):
    """
    Move file to rejected prefix with error details.
    """
    filename = os.path.basename(object_key)
    rejected_key = f"{rejected_prefix}{filename}"

    # Copy file to rejected prefix with error metadata
    s3.copy_object(
        Bucket=bucket_name,
        CopySource={'Bucket': bucket_name, 'Key': object_key},
        Key=rejected_key,
        Metadata={
            'validation-error': error_message[:1000],
            'original-key': object_key,
            'rejected-timestamp': str(pd.Timestamp.now())
        },
        MetadataDirective='REPLACE'
    )

    # Create error details file
    error_details = {
        'original_file': object_key,
        'rejected_file': rejected_key,
        'error': error_message,
        'timestamp': str(pd.Timestamp.now())
    }
    s3.put_object(
        Bucket=bucket_name,
        Key=f"{rejected_key}.error.json",
        Body=json.dumps(error_details, indent=2),
        ContentType='application/json'
    )

    logger.info("File rejected", extra={"rejected_key": rejected_key})
    return rejected_key


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    # Get configuration from environment
    processed_prefix = os.environ.get('PROCESSED_PREFIX', 'processed/')
    rejected_prefix = os.environ.get('REJECTED_PREFIX', 'rejected/')

    # Extract S3 bucket and key information from the event
    detail = event['detail']
    bucket_name = detail['bucket']['name']
    object_key = detail['object']['key']
    filename = os.path.basename(object_key)

    logger.info("Processing file", extra={"file_name": filename, "bucket": bucket_name})

    try:
        # Step 1: Validate filename format
        store_id, year, month, day = parse_filename(filename)

        if store_id is None:
            error_message = f"Invalid filename format. Expected: store_XXXX_YYYY-MM-DD.json, got: {filename}"
            logger.warning("Invalid filename format", extra={"file_name": filename})
            metrics.add_metric(name="FilesRejected", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="FilenameValidationErrors", unit=MetricUnit.Count, value=1)
            rejected_key = reject_file(s3, bucket_name, object_key, rejected_prefix, error_message)
            return {
                'statusCode': 400,
                'status': 'rejected',
                'message': 'File rejected due to invalid filename format',
                'error': error_message,
                'rejected_key': rejected_key,
                'original_key': object_key
            }

        logger.info("Filename parsed", extra={"store_id": store_id, "date": f"{year}-{month}-{day}"})

        # Step 2: Download and parse JSON
        json_tmp_file = '/tmp/input.json'
        s3.download_file(bucket_name, object_key, json_tmp_file)
        logger.debug("Downloaded JSON file to /tmp")

        with open(json_tmp_file, 'r') as f:
            json_data = json.load(f)

        # Step 3: Validate JSON against schema
        is_valid, error_message = validate_json_schema(json_data)

        if not is_valid:
            logger.warning("Schema validation failed", extra={"error": error_message})
            metrics.add_metric(name="FilesRejected", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="SchemaValidationErrors", unit=MetricUnit.Count, value=1)
            rejected_key = reject_file(s3, bucket_name, object_key, rejected_prefix, error_message)
            return {
                'statusCode': 400,
                'status': 'rejected',
                'message': 'File rejected due to schema validation failure',
                'error': error_message,
                'rejected_key': rejected_key,
                'original_key': object_key
            }

        logger.info("Schema validation passed")

        # Step 4: Convert to DataFrame with proper types
        df = pd.DataFrame(json_data)

        # Convert timestamp strings to datetime
        df['transaction_timestamp'] = pd.to_datetime(df['transaction_timestamp'])

        # Convert decimal fields to Decimal for precision
        decimal_columns = ['unit_price', 'line_total', 'discount_amount']
        for col in decimal_columns:
            df[col] = df[col].apply(lambda x: Decimal(str(x)))

        # Ensure quantity is int32
        df['quantity'] = df['quantity'].astype('int32')

        logger.info("DataFrame converted", extra={"records": len(df)})

        # Step 6: Write Parquet with PyArrow schema (portable)
        # Convert DataFrame to PyArrow Table with explicit schema
        table = pa.Table.from_pandas(df, schema=PARQUET_SCHEMA, preserve_index=False)

        # Write to local temp file first
        parquet_tmp_file = '/tmp/output.parquet'
        pq.write_table(table, parquet_tmp_file)

        # Upload to S3 with Hive-style path
        output_key = f"{processed_prefix}year={year}/month={month}/day={day}/store_id={store_id}/data.parquet"
        s3.upload_file(parquet_tmp_file, bucket_name, output_key)

        logger.info("Parquet uploaded", extra={"output_key": output_key})
        metrics.add_metric(name="FilesProcessed", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="RecordsProcessed", unit=MetricUnit.Count, value=len(df))

        # Return data needed for next steps in the pipeline
        return {
            'statusCode': 200,
            'status': 'success',
            'bucket': bucket_name,
            'key': object_key,
            'store_id': store_id,
            'year': year,
            'month': month,
            'day': day,
            'output_key': output_key,
            'records_processed': len(df)
        }

    except Exception as e:
        logger.exception("Error processing upload")
        metrics.add_metric(name="Errors", unit=MetricUnit.Count, value=1)
        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e),
            'original_key': object_key
        }
