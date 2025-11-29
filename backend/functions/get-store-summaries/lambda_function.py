"""
Get Store Summaries Lambda

Query all store summaries for a specific date from DynamoDB.

Input: { "date": "2025-01-15" }
Output: { "date": "...", "store_summaries": [...], "store_count": N }
"""

import boto3
import json
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
    table = dynamodb.Table(table_name)

    date = event.get('date')
    if not date:
        raise ValueError("Missing required field: date")

    logger.info("Querying store summaries", extra={"date": date})

    # Query GSI to get all store summaries for this date
    store_summaries = query_store_summaries(table, date)

    metrics.add_metric(name="StoreSummariesRetrieved", unit=MetricUnit.Count, value=len(store_summaries))
    metrics.add_dimension(name="Date", value=date)

    logger.info("Store summaries retrieved", extra={
        "date": date,
        "store_count": len(store_summaries)
    })

    return {
        'date': date,
        'store_summaries': store_summaries,
        'store_count': len(store_summaries)
    }


@tracer.capture_method
def query_store_summaries(table, date):
    """Query GSI for all store summaries for the given date."""
    # GSI1PK = DATE#yyyy-mm-dd, GSI1SK begins with STORE#
    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression=Key('GSI1PK').eq(f'DATE#{date}') & Key('GSI1SK').begins_with('STORE#')
    )

    items = response.get('Items', [])

    # Transform items to a cleaner format
    store_summaries = []
    for item in items:
        store_summaries.append({
            'store_id': item.get('store_id'),
            'date': date,
            'total_sales': float(item.get('total_sales', 0)),
            'transaction_count': int(item.get('transaction_count', 0)),
            'item_count': int(item.get('item_count', 0)),
            'avg_transaction': float(item.get('avg_transaction', 0)),
            'top_products': item.get('top_products', []),
            'payment_breakdown': item.get('payment_breakdown', {})
        })

    # Sort by store_id for consistent ordering
    store_summaries.sort(key=lambda x: x['store_id'])

    return store_summaries
