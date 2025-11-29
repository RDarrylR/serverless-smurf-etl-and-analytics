"""
Calculate Metrics Lambda

Calculates aggregated metrics from uploaded JSON transaction data.
Called by Step Functions after successful file validation.

Input (from Step Functions):
{
    "bucket": "<your-bucket-name>",
    "key": "uploads/store_0001_2025-01-15.json",
    "store_id": "0001",
    "year": "2025",
    "month": "01",
    "day": "15"
}

Output:
{
    "store_id": "0001",
    "date": "2025-01-15",
    "metrics": {
        "total_sales": 1234.56,
        "total_discount": 45.67,
        "net_sales": 1188.89,
        "transaction_count": 45,
        "item_count": 78,
        "avg_transaction": 27.43,
        "top_products": [...],
        "payment_breakdown": {...}
    }
}
"""

import json
import boto3
from collections import defaultdict
from decimal import Decimal

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
    bucket = event['bucket']
    key = event['key']
    store_id = event['store_id']
    year = event['year']
    month = event['month']
    day = event['day']
    date = f"{year}-{month}-{day}"

    logger.info("Processing transactions", extra={
        "store_id": store_id,
        "date": date,
        "bucket": bucket,
        "key": key
    })

    # Download and parse JSON file
    response = s3_client.get_object(Bucket=bucket, Key=key)
    transactions = json.loads(response['Body'].read().decode('utf-8'))

    logger.info("Transactions loaded", extra={
        "transaction_count": len(transactions),
        "store_id": store_id,
        "date": date
    })

    # Calculate metrics
    calculated_metrics = calculate_metrics(transactions)

    result = {
        "store_id": store_id,
        "date": date,
        "year": year,
        "month": month,
        "day": day,
        "metrics": calculated_metrics,
        "record_count": len(transactions),
        "source_key": key
    }

    metrics.add_metric(name="TransactionsProcessed", unit=MetricUnit.Count, value=len(transactions))
    metrics.add_metric(name="StoresProcessed", unit=MetricUnit.Count, value=1)
    metrics.add_dimension(name="StoreId", value=store_id)

    logger.info("Metrics calculated", extra={
        "store_id": store_id,
        "date": date,
        "total_sales": calculated_metrics["total_sales"],
        "transaction_count": calculated_metrics["transaction_count"]
    })

    return result


@tracer.capture_method
def calculate_metrics(transactions):
    """
    Calculate aggregated metrics from transaction list.
    """
    if not transactions:
        return {
            "total_sales": 0,
            "total_discount": 0,
            "net_sales": 0,
            "transaction_count": 0,
            "item_count": 0,
            "avg_transaction": 0,
            "top_products": [],
            "payment_breakdown": {}
        }

    # Aggregate values
    total_sales = Decimal('0')
    total_discount = Decimal('0')
    total_items = 0
    payment_totals = defaultdict(lambda: Decimal('0'))
    product_stats = defaultdict(lambda: {"units": 0, "revenue": Decimal('0'), "name": ""})

    for txn in transactions:
        line_total = Decimal(str(txn['line_total']))
        discount = Decimal(str(txn['discount_amount']))
        quantity = txn['quantity']
        sku = txn['item_sku']
        name = txn['item_name']
        payment = txn['payment_method']

        total_sales += line_total
        total_discount += discount
        total_items += quantity

        payment_totals[payment] += line_total - discount

        product_stats[sku]['units'] += quantity
        product_stats[sku]['revenue'] += line_total - discount
        product_stats[sku]['name'] = name

    # Calculate derived metrics
    net_sales = total_sales - total_discount
    transaction_count = len(transactions)
    avg_transaction = net_sales / transaction_count if transaction_count > 0 else Decimal('0')

    # Get top 5 products by revenue
    top_products = sorted(
        [
            {
                "sku": sku,
                "name": stats['name'],
                "units": stats['units'],
                "revenue": float(stats['revenue'])
            }
            for sku, stats in product_stats.items()
        ],
        key=lambda x: x['revenue'],
        reverse=True
    )[:5]

    # Convert payment breakdown to regular dict with floats
    payment_breakdown = {
        method: float(amount)
        for method, amount in payment_totals.items()
    }

    return {
        "total_sales": float(total_sales),
        "total_discount": float(total_discount),
        "net_sales": float(net_sales),
        "transaction_count": transaction_count,
        "item_count": total_items,
        "avg_transaction": float(round(avg_transaction, 2)),
        "top_products": top_products,
        "payment_breakdown": payment_breakdown
    }
