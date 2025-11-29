"""
Calculate Product Metrics Lambda

Aggregate product metrics across all stores for a date and write to DynamoDB.

Input: { "date": "2025-01-15", "store_summaries": [...], "company_metrics": {...} }
Output: { "date": "...", "product_metrics": [...], "company_metrics": {...} }
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
    company_metrics = event.get('company_metrics')

    if not date:
        raise ValueError("Missing required field: date")

    if not store_summaries:
        logger.warning("No store summaries provided", extra={"date": date})
        return {
            'date': date,
            'product_metrics': [],
            'company_metrics': company_metrics,
            'message': 'No store data available'
        }

    logger.info("Calculating product metrics", extra={
        "date": date,
        "store_count": len(store_summaries)
    })

    # Aggregate products across all stores
    product_metrics = aggregate_products(store_summaries)

    # Write product summaries to DynamoDB
    write_product_summaries(table, date, product_metrics)

    metrics.add_metric(name="ProductsAggregated", unit=MetricUnit.Count, value=len(product_metrics))
    metrics.add_dimension(name="Date", value=date)

    logger.info("Product metrics calculated", extra={
        "date": date,
        "product_count": len(product_metrics)
    })

    return {
        'date': date,
        'product_metrics': product_metrics[:10],  # Top 10 for the report
        'product_count': len(product_metrics),
        'company_metrics': company_metrics
    }


@tracer.capture_method
def aggregate_products(store_summaries):
    """Aggregate product data across all stores."""
    # Each store has top_products: [{"sku": "...", "name": "...", "units": N, "revenue": X}, ...]
    product_aggregates = {}

    for summary in store_summaries:
        store_id = summary['store_id']
        top_products = summary.get('top_products', [])

        for product in top_products:
            sku = product.get('sku')
            if not sku:
                continue

            if sku not in product_aggregates:
                product_aggregates[sku] = {
                    'sku': sku,
                    'name': product.get('name', 'Unknown'),
                    'units_sold': 0,
                    'revenue': 0,
                    'stores_sold_at': []
                }

            product_aggregates[sku]['units_sold'] += product.get('units', 0)
            product_aggregates[sku]['revenue'] += product.get('revenue', 0)
            if store_id not in product_aggregates[sku]['stores_sold_at']:
                product_aggregates[sku]['stores_sold_at'].append(store_id)

    # Convert to list and sort by revenue (descending)
    product_metrics = list(product_aggregates.values())
    product_metrics.sort(key=lambda x: x['revenue'], reverse=True)

    # Round revenue values
    for p in product_metrics:
        p['revenue'] = round(p['revenue'], 2)

    return product_metrics


@tracer.capture_method
def write_product_summaries(table, date, product_metrics):
    """Write product summaries to DynamoDB using batch writer."""
    with table.batch_writer() as batch:
        for product in product_metrics:
            item = {
                'PK': f'DATE#{date}',
                'SK': f'PRODUCT#{product["sku"]}',
                'GSI1PK': f'PRODUCT#{product["sku"]}',
                'GSI1SK': f'DATE#{date}',
                'product_sku': product['sku'],
                'product_name': product['name'],
                'units_sold': product['units_sold'],
                'revenue': Decimal(str(product['revenue'])),
                'stores_sold_at': product['stores_sold_at'],
                'store_count': len(product['stores_sold_at'])
            }
            batch.put_item(Item=item)

    logger.debug("Wrote product summaries to DynamoDB", extra={
        "product_count": len(product_metrics)
    })
