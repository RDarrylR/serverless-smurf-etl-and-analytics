"""
Calculate Company Metrics Lambda

Aggregate metrics across all stores for a date and write to DynamoDB.

Input: { "date": "2025-01-15", "store_summaries": [...] }
Output: { "date": "...", "company_metrics": {...} }
"""

import boto3
import json
import os
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

    date = event.get('date')
    store_summaries = event.get('store_summaries', [])

    if not date:
        raise ValueError("Missing required field: date")

    if not store_summaries:
        logger.warning("No store summaries provided", extra={"date": date})
        return {
            'date': date,
            'company_metrics': None,
            'message': 'No store data available'
        }

    logger.info("Calculating company metrics", extra={
        "date": date,
        "store_count": len(store_summaries)
    })

    # Calculate company-wide aggregates
    company_metrics = calculate_company_metrics(store_summaries, date)

    # Write company summary to DynamoDB
    write_company_summary(table, date, company_metrics)

    metrics.add_metric(name="CompanyMetricsCalculated", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="TotalSales", unit=MetricUnit.Count, value=int(company_metrics['total_sales']))
    metrics.add_dimension(name="Date", value=date)

    logger.info("Company metrics calculated", extra={
        "date": date,
        "total_sales": company_metrics['total_sales'],
        "store_count": company_metrics['store_count']
    })

    return {
        'date': date,
        'company_metrics': company_metrics,
        'store_summaries': store_summaries  # Pass through for next step
    }


@tracer.capture_method
def calculate_company_metrics(store_summaries, date):
    """Calculate company-wide aggregates from store summaries."""
    total_sales = sum(s['total_sales'] for s in store_summaries)
    total_transactions = sum(s['transaction_count'] for s in store_summaries)
    total_items = sum(s['item_count'] for s in store_summaries)

    # Find best and worst performing stores
    sorted_by_sales = sorted(store_summaries, key=lambda x: x['total_sales'], reverse=True)
    best_store = sorted_by_sales[0] if sorted_by_sales else None
    worst_store = sorted_by_sales[-1] if sorted_by_sales else None

    # Aggregate payment breakdown across all stores
    payment_totals = {}
    for summary in store_summaries:
        for method, amount in summary.get('payment_breakdown', {}).items():
            if method not in payment_totals:
                payment_totals[method] = 0
            payment_totals[method] += float(amount)

    return {
        'date': date,
        'total_sales': round(total_sales, 2),
        'total_transactions': total_transactions,
        'total_items': total_items,
        'store_count': len(store_summaries),
        'stores_reported': [s['store_id'] for s in store_summaries],
        'avg_transaction': round(total_sales / total_transactions, 2) if total_transactions > 0 else 0,
        'avg_store_sales': round(total_sales / len(store_summaries), 2) if store_summaries else 0,
        'best_store': {
            'store_id': best_store['store_id'],
            'total_sales': best_store['total_sales']
        } if best_store else None,
        'worst_store': {
            'store_id': worst_store['store_id'],
            'total_sales': worst_store['total_sales']
        } if worst_store else None,
        'payment_breakdown': {k: round(v, 2) for k, v in payment_totals.items()}
    }


@tracer.capture_method
def write_company_summary(table, date, company_metrics):
    """Write company summary to DynamoDB."""
    item = {
        'PK': f'DATE#{date}',
        'SK': 'SUMMARY#COMPANY',
        **{k: Decimal(str(v)) if isinstance(v, float) else v for k, v in company_metrics.items()}
    }

    # Handle nested dicts with Decimal conversion
    if item.get('best_store'):
        item['best_store']['total_sales'] = Decimal(str(item['best_store']['total_sales']))
    if item.get('worst_store'):
        item['worst_store']['total_sales'] = Decimal(str(item['worst_store']['total_sales']))
    if item.get('payment_breakdown'):
        item['payment_breakdown'] = {k: Decimal(str(v)) for k, v in item['payment_breakdown'].items()}

    table.put_item(Item=item)
    logger.debug("Wrote company summary to DynamoDB", extra={
        "PK": f"DATE#{date}",
        "SK": "SUMMARY#COMPANY"
    })
