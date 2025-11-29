"""
Check All Stores Lambda

Checks if all expected stores have uploaded their data for a given date.
Queries DynamoDB for upload tracking records and compares against expected stores.

Input (from write-metrics):
{
    "store_id": "0001",
    "date": "2025-01-15",
    "written": true,
    "items_written": 2
}

Output:
{
    "date": "2025-01-15",
    "all_stores_done": true/false,
    "stores_reported": ["0001", "0002", ...],
    "stores_missing": ["0007", "0011"],
    "total_expected": 11,
    "total_reported": 9
}
"""

import json
import boto3
import os
from boto3.dynamodb.conditions import Key

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb = boto3.resource('dynamodb')


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    table_name = os.environ.get('DYNAMODB_TABLE', 'SalesData')
    expected_stores = os.environ.get('EXPECTED_STORES', '0001,0002,0003,0004,0005,0006,0007,0008,0009,0010,0011')
    expected_stores_list = [s.strip() for s in expected_stores.split(',')]

    table = dynamodb.Table(table_name)

    date = event['date']

    logger.info("Checking store uploads", extra={
        "date": date,
        "expected_stores_count": len(expected_stores_list)
    })

    # Query for all upload tracking records for this date
    stores_reported = query_uploaded_stores(table, date)

    # Find missing stores
    stores_missing = [s for s in expected_stores_list if s not in stores_reported]

    all_stores_done = len(stores_missing) == 0

    # Add metrics
    metrics.add_metric(name="StoresReported", unit=MetricUnit.Count, value=len(stores_reported))
    metrics.add_metric(name="StoresMissing", unit=MetricUnit.Count, value=len(stores_missing))
    metrics.add_dimension(name="Date", value=date)

    if all_stores_done:
        metrics.add_metric(name="AllStoresDone", unit=MetricUnit.Count, value=1)
        logger.info("All stores have reported", extra={"date": date})
    else:
        logger.info("Some stores missing", extra={
            "date": date,
            "missing": stores_missing
        })

    result = {
        'date': date,
        'all_stores_done': all_stores_done,
        'stores_reported': sorted(stores_reported),
        'stores_missing': sorted(stores_missing),
        'total_expected': len(expected_stores_list),
        'total_reported': len(stores_reported)
    }

    logger.info("Check complete", extra=result)

    return result


@tracer.capture_method
def query_uploaded_stores(table, date):
    """Query DynamoDB for all stores that have uploaded for the given date."""
    # Query for all upload tracking records for this date
    # Upload tracking records have PK=DATE#yyyy-mm-dd, SK begins with UPLOAD#STORE#
    response = table.query(
        KeyConditionExpression=Key('PK').eq(f'DATE#{date}') & Key('SK').begins_with('UPLOAD#STORE#')
    )

    # Extract store IDs from the results
    stores_reported = []
    for item in response.get('Items', []):
        # SK format: UPLOAD#STORE#0001
        sk = item['SK']
        store_id = sk.replace('UPLOAD#STORE#', '')
        stores_reported.append(store_id)

    return stores_reported
