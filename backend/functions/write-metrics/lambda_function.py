"""
Write Metrics Lambda

Writes calculated metrics to DynamoDB.
Creates two records:
1. Store daily summary (PK: STORE#xxxx, SK: DATE#yyyy-mm-dd)
2. Upload tracking (PK: DATE#yyyy-mm-dd, SK: UPLOAD#STORE#xxxx)

Input (from calculate-metrics):
{
    "store_id": "0001",
    "date": "2025-01-15",
    "year": "2025",
    "month": "01",
    "day": "15",
    "metrics": {...},
    "record_count": 45,
    "source_key": "uploads/store_0001_2025-01-15.json"
}

Output:
{
    "store_id": "0001",
    "date": "2025-01-15",
    "written": true,
    "items_written": 2
}
"""

import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

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

    store_id = event['store_id']
    date = event['date']
    year = event['year']
    month = event['month']
    day = event['day']
    store_metrics = event['metrics']
    record_count = event['record_count']
    source_key = event['source_key']

    now = datetime.utcnow().isoformat() + 'Z'

    logger.info("Writing metrics to DynamoDB", extra={
        "store_id": store_id,
        "date": date,
        "table": table_name
    })

    # Convert floats to Decimal for DynamoDB
    metrics_decimal = json_to_dynamodb(store_metrics)

    items_written = 0

    # 1. Write store daily summary
    store_summary = {
        'PK': f'STORE#{store_id}',
        'SK': f'DATE#{date}',
        'GSI1PK': f'DATE#{date}',
        'GSI1SK': f'STORE#{store_id}',
        'store_id': store_id,
        'date': date,
        'year': year,
        'month': month,
        'day': day,
        'total_sales': metrics_decimal['total_sales'],
        'total_discount': metrics_decimal['total_discount'],
        'net_sales': metrics_decimal['net_sales'],
        'transaction_count': metrics_decimal['transaction_count'],
        'item_count': metrics_decimal['item_count'],
        'avg_transaction': metrics_decimal['avg_transaction'],
        'top_products': metrics_decimal['top_products'],
        'payment_breakdown': metrics_decimal['payment_breakdown'],
        'record_count': record_count,
        'created_at': now,
        'updated_at': now
    }

    logger.debug("Writing store summary", extra={
        "PK": store_summary['PK'],
        "SK": store_summary['SK']
    })
    table.put_item(Item=store_summary)
    items_written += 1

    # 2. Write upload tracking record
    upload_tracking = {
        'PK': f'DATE#{date}',
        'SK': f'UPLOAD#STORE#{store_id}',
        'store_id': store_id,
        'date': date,
        'uploaded_at': now,
        's3_key': source_key,
        'record_count': record_count,
        'status': 'processed',
        'total_sales': metrics_decimal['total_sales']
    }

    logger.debug("Writing upload tracking", extra={
        "PK": upload_tracking['PK'],
        "SK": upload_tracking['SK']
    })
    table.put_item(Item=upload_tracking)
    items_written += 1

    metrics.add_metric(name="ItemsWritten", unit=MetricUnit.Count, value=items_written)
    metrics.add_metric(name="StoreMetricsWritten", unit=MetricUnit.Count, value=1)
    metrics.add_dimension(name="StoreId", value=store_id)

    result = {
        'store_id': store_id,
        'date': date,
        'written': True,
        'items_written': items_written
    }

    logger.info("Write complete", extra=result)

    return result


@tracer.capture_method
def json_to_dynamodb(obj):
    """
    Convert JSON object to DynamoDB-compatible format.
    Converts floats to Decimal.
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: json_to_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_to_dynamodb(item) for item in obj]
    else:
        return obj
