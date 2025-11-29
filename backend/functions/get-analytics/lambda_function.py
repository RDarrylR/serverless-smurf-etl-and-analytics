"""
Get Analytics Lambda

Fetches analytics data from DynamoDB for the frontend dashboard.
Returns store summaries, top products, and AI insights for a given date range.

Input: Query params - date (optional, defaults to latest), days (optional, defaults to 30)
Output: JSON with store_summaries, top_products, anomalies, trends, recommendations
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')


def decimal_to_float(obj):
    """Recursively convert Decimal to float in nested structures."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def cors_response(status_code: int, body: dict) -> dict:
    """Return response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(body)
    }


@tracer.capture_method
def get_available_dates(table) -> list:
    """Get list of dates that have data, sorted descending."""
    # Scan for unique dates from store summaries
    dates = set()

    response = table.scan(
        ProjectionExpression='PK',
        FilterExpression='begins_with(PK, :prefix)',
        ExpressionAttributeValues={':prefix': 'STORE#'}
    )

    for item in response.get('Items', []):
        # PK is STORE#xxxx, SK is DATE#yyyy-mm-dd
        pass

    # Query using GSI1 to find dates
    # GSI1PK = DATE#yyyy-mm-dd
    response = table.scan(
        ProjectionExpression='GSI1PK',
        FilterExpression='begins_with(GSI1PK, :prefix)',
        ExpressionAttributeValues={':prefix': 'DATE#'}
    )

    for item in response.get('Items', []):
        gsi1pk = item.get('GSI1PK', '')
        if gsi1pk.startswith('DATE#'):
            dates.add(gsi1pk.replace('DATE#', ''))

    return sorted(list(dates), reverse=True)


@tracer.capture_method
def query_store_summaries(table, date_str: str) -> list:
    """Query store summaries for a specific date using GSI1."""
    all_items = []

    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression='GSI1PK = :pk',
        ExpressionAttributeValues={
            ':pk': f'DATE#{date_str}'
        }
    )

    for item in response.get('Items', []):
        # GSI1SK contains STORE#xxx for store records
        if item.get('GSI1SK', '').startswith('STORE#'):
            converted = decimal_to_float(item)
            # Extract store_id from GSI1SK
            converted['store_id'] = item.get('GSI1SK', '').replace('STORE#', '')
            all_items.append(converted)

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.query(
            IndexName='GSI1',
            KeyConditionExpression='GSI1PK = :pk',
            ExpressionAttributeValues={
                ':pk': f'DATE#{date_str}'
            },
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        for item in response.get('Items', []):
            if item.get('GSI1SK', '').startswith('STORE#'):
                converted = decimal_to_float(item)
                converted['store_id'] = item.get('GSI1SK', '').replace('STORE#', '')
                all_items.append(converted)

    logger.info("Queried store summaries", extra={
        "record_count": len(all_items),
        "date": date_str
    })

    return all_items


@tracer.capture_method
def query_insights(table, date_str: str) -> dict:
    """Query insights (anomalies, trends, recommendations) for a specific date."""
    anomalies = []
    trends = []
    recommendations = []

    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
        ExpressionAttributeValues={
            ':pk': f'DATE#{date_str}',
            ':sk_prefix': 'INSIGHT#'
        }
    )

    for item in response.get('Items', []):
        item_converted = decimal_to_float(item)
        item_converted['date'] = date_str

        insight_type = item.get('insight_type')
        if insight_type == 'anomaly':
            anomalies.append(item_converted)
        elif insight_type == 'trend':
            trends.append(item_converted)
        elif insight_type == 'recommendation':
            recommendations.append(item_converted)

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
            ExpressionAttributeValues={
                ':pk': f'DATE#{date_str}',
                ':sk_prefix': 'INSIGHT#'
            },
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        for item in response.get('Items', []):
            item_converted = decimal_to_float(item)
            item_converted['date'] = date_str

            insight_type = item.get('insight_type')
            if insight_type == 'anomaly':
                anomalies.append(item_converted)
            elif insight_type == 'trend':
                trends.append(item_converted)
            elif insight_type == 'recommendation':
                recommendations.append(item_converted)

    logger.info("Queried insights", extra={
        "anomaly_count": len(anomalies),
        "trend_count": len(trends),
        "recommendation_count": len(recommendations),
        "date": date_str
    })

    return {
        'anomalies': anomalies,
        'trends': trends,
        'recommendations': recommendations
    }


@tracer.capture_method
def calculate_aggregates(store_summaries: list) -> dict:
    """Calculate aggregate metrics from store summaries."""
    if not store_summaries:
        return {
            'total_sales': 0,
            'total_transactions': 0,
            'total_items': 0,
            'avg_transaction': 0,
            'store_count': 0,
            'payment_breakdown': {
                'cash': 0,
                'credit': 0,
                'debit': 0,
                'gift_card': 0
            }
        }

    total_sales = sum(s.get('total_sales', 0) for s in store_summaries)
    total_transactions = sum(s.get('transaction_count', 0) for s in store_summaries)
    total_items = sum(s.get('item_count', 0) for s in store_summaries)

    payment_cash = sum(s.get('payment_breakdown', {}).get('cash', 0) for s in store_summaries)
    payment_credit = sum(s.get('payment_breakdown', {}).get('credit', 0) for s in store_summaries)
    payment_debit = sum(s.get('payment_breakdown', {}).get('debit', 0) for s in store_summaries)
    payment_gift_card = sum(s.get('payment_breakdown', {}).get('gift_card', 0) for s in store_summaries)

    return {
        'total_sales': round(total_sales, 2),
        'total_transactions': int(total_transactions),
        'total_items': int(total_items),
        'avg_transaction': round(total_sales / total_transactions, 2) if total_transactions > 0 else 0,
        'store_count': len(store_summaries),
        'payment_breakdown': {
            'cash': round(payment_cash, 2),
            'credit': round(payment_credit, 2),
            'debit': round(payment_debit, 2),
            'gift_card': round(payment_gift_card, 2)
        }
    }


@tracer.capture_method
def extract_top_products(store_summaries: list, limit: int = 10) -> list:
    """Extract and aggregate top products across all stores."""
    product_totals = {}

    for store in store_summaries:
        for product in store.get('top_products', []):
            sku = product.get('sku', 'unknown')
            if sku not in product_totals:
                product_totals[sku] = {
                    'sku': sku,
                    'name': product.get('name', 'Unknown'),
                    'units_sold': 0,
                    'revenue': 0
                }
            product_totals[sku]['units_sold'] += product.get('units', 0)
            product_totals[sku]['revenue'] += product.get('revenue', 0)

    # Sort by revenue and return top N
    sorted_products = sorted(
        product_totals.values(),
        key=lambda x: x['revenue'],
        reverse=True
    )

    return sorted_products[:limit]


@tracer.capture_method
def format_store_data(store_summaries: list) -> list:
    """Format store summaries for frontend chart consumption."""
    formatted = []
    for store in store_summaries:
        formatted.append({
            'store_id': store.get('store_id', ''),
            'total_sales': round(store.get('total_sales', 0), 2),
            'transaction_count': int(store.get('transaction_count', 0)),
            'item_count': int(store.get('item_count', 0)),
            'avg_transaction': round(store.get('avg_transaction', 0), 2),
            'payment_breakdown': store.get('payment_breakdown', {})
        })

    # Sort by store_id
    return sorted(formatted, key=lambda x: x['store_id'])


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    table_name = os.environ.get('DYNAMODB_TABLE', 'SalesData')
    table = dynamodb.Table(table_name)

    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {'message': 'OK'})

    # Get query parameters
    query_params = event.get('queryStringParameters') or {}
    requested_date = query_params.get('date')

    # Get available dates
    available_dates = get_available_dates(table)

    if not available_dates:
        return cors_response(200, {
            'message': 'No data available',
            'available_dates': [],
            'kpis': calculate_aggregates([]),
            'stores': [],
            'top_products': [],
            'anomalies': [],
            'trends': [],
            'recommendations': []
        })

    # Use requested date or latest available
    target_date = requested_date if requested_date in available_dates else available_dates[0]

    # Query data for target date
    store_summaries = query_store_summaries(table, target_date)
    insights = query_insights(table, target_date)

    # Build response
    response_data = {
        'date': target_date,
        'available_dates': available_dates,
        'kpis': calculate_aggregates(store_summaries),
        'stores': format_store_data(store_summaries),
        'top_products': extract_top_products(store_summaries),
        'anomalies': insights['anomalies'],
        'trends': insights['trends'],
        'recommendations': insights['recommendations']
    }

    logger.info("Analytics response prepared", extra={
        "date": target_date,
        "store_count": len(store_summaries),
        "anomaly_count": len(insights['anomalies']),
        "trend_count": len(insights['trends']),
        "recommendation_count": len(insights['recommendations'])
    })

    return cors_response(200, response_data)
