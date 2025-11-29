"""
Get Trends Lambda

Fetches historical sales data for trending analytics.
Uses GSI1 (DATE#yyyy-mm-dd -> STORE#xxxx) for efficient querying.
Also queries product trends using GSI1 (PRODUCT#sku -> DATE#yyyy-mm-dd).

Input: Query params - store_id (optional), days (optional, defaults to 30)
Output: JSON with time-series data per store and product trends for visualization
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
def query_date_data(table, date_str: str, store_filter: str = None) -> list:
    """
    Query all store data for a specific date using GSI1.
    GSI1PK = DATE#yyyy-mm-dd, GSI1SK = STORE#xxxx
    This is efficient - single query per date.
    """
    items = []

    query_params = {
        'IndexName': 'GSI1',
        'KeyConditionExpression': 'GSI1PK = :pk',
        'ExpressionAttributeValues': {
            ':pk': f'DATE#{date_str}'
        }
    }

    # If filtering by store, add key condition on GSI1SK
    if store_filter:
        query_params['KeyConditionExpression'] += ' AND GSI1SK = :sk'
        query_params['ExpressionAttributeValues'][':sk'] = f'STORE#{store_filter}'

    response = table.query(**query_params)

    for item in response.get('Items', []):
        gsi1sk = item.get('GSI1SK', '')
        if gsi1sk.startswith('STORE#'):
            converted = decimal_to_float(item)
            converted['store_id'] = gsi1sk.replace('STORE#', '')
            converted['date'] = date_str
            items.append(converted)

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        query_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
        response = table.query(**query_params)
        for item in response.get('Items', []):
            gsi1sk = item.get('GSI1SK', '')
            if gsi1sk.startswith('STORE#'):
                converted = decimal_to_float(item)
                converted['store_id'] = gsi1sk.replace('STORE#', '')
                converted['date'] = date_str
                items.append(converted)

    return items


@tracer.capture_method
def query_products_for_date(table, date_str: str) -> list:
    """
    Query all product data for a specific date using PK.
    PK = DATE#yyyy-mm-dd, SK starts with PRODUCT#
    """
    items = []

    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
        ExpressionAttributeValues={
            ':pk': f'DATE#{date_str}',
            ':sk_prefix': 'PRODUCT#'
        }
    )

    for item in response.get('Items', []):
        converted = decimal_to_float(item)
        converted['date'] = date_str
        items.append(converted)

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
            ExpressionAttributeValues={
                ':pk': f'DATE#{date_str}',
                ':sk_prefix': 'PRODUCT#'
            },
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        for item in response.get('Items', []):
            converted = decimal_to_float(item)
            converted['date'] = date_str
            items.append(converted)

    return items


@tracer.capture_method
def get_available_dates(table) -> list:
    """
    Get list of dates that have data.
    Scans GSI1 but only retrieves GSI1PK - minimal data transfer.
    """
    dates = set()

    response = table.scan(
        IndexName='GSI1',
        ProjectionExpression='GSI1PK',
    )

    for item in response.get('Items', []):
        gsi1pk = item.get('GSI1PK', '')
        if gsi1pk and gsi1pk.startswith('DATE#'):
            dates.add(gsi1pk.replace('DATE#', ''))

    while 'LastEvaluatedKey' in response:
        response = table.scan(
            IndexName='GSI1',
            ProjectionExpression='GSI1PK',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        for item in response.get('Items', []):
            gsi1pk = item.get('GSI1PK', '')
            if gsi1pk and gsi1pk.startswith('DATE#'):
                dates.add(gsi1pk.replace('DATE#', ''))

    return sorted(list(dates))


@tracer.capture_method
def build_product_trends(all_product_data: list, dates: list) -> list:
    """
    Build product trends data with historical comparisons.
    Returns top products with their daily history and trend metrics.
    """
    # Aggregate product data across all dates
    product_totals = {}

    for record in all_product_data:
        sku = record.get('product_sku')
        if not sku:
            continue

        if sku not in product_totals:
            product_totals[sku] = {
                'sku': sku,
                'name': record.get('product_name', 'Unknown'),
                'total_units': 0,
                'total_revenue': 0,
                'daily_data': {},
                'days_sold': 0
            }

        date = record.get('date')
        units = record.get('units_sold', 0)
        revenue = record.get('revenue', 0)

        product_totals[sku]['total_units'] += units
        product_totals[sku]['total_revenue'] += revenue

        if date not in product_totals[sku]['daily_data']:
            product_totals[sku]['daily_data'][date] = {'units_sold': 0, 'revenue': 0}
            product_totals[sku]['days_sold'] += 1

        product_totals[sku]['daily_data'][date]['units_sold'] += units
        product_totals[sku]['daily_data'][date]['revenue'] += revenue

    # Convert to list and sort by total revenue
    products = list(product_totals.values())
    products.sort(key=lambda x: x['total_revenue'], reverse=True)

    # Build trend data for top 15 products
    product_trends = []
    for product in products[:15]:
        daily_history = []
        for date in dates:
            day_data = product['daily_data'].get(date, {'units_sold': 0, 'revenue': 0})
            daily_history.append({
                'date': date,
                'units_sold': day_data['units_sold'],
                'revenue': round(day_data['revenue'], 2)
            })

        # Calculate average and trend
        units_values = [d['units_sold'] for d in daily_history if d['units_sold'] > 0]
        revenue_values = [d['revenue'] for d in daily_history if d['revenue'] > 0]

        avg_units = sum(units_values) / len(units_values) if units_values else 0
        avg_revenue = sum(revenue_values) / len(revenue_values) if revenue_values else 0

        # Calculate trend direction (compare first half vs second half)
        if len(units_values) >= 2:
            mid = len(units_values) // 2
            first_half_avg = sum(units_values[:mid]) / mid if mid > 0 else 0
            second_half_avg = sum(units_values[mid:]) / (len(units_values) - mid) if (len(units_values) - mid) > 0 else 0

            if second_half_avg > first_half_avg * 1.1:
                trend_direction = 'increasing'
            elif second_half_avg < first_half_avg * 0.9:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'

            trend_percent = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        else:
            trend_direction = 'insufficient_data'
            trend_percent = 0

        product_trends.append({
            'sku': product['sku'],
            'name': product['name'],
            'total_units_sold': product['total_units'],
            'total_revenue': round(product['total_revenue'], 2),
            'avg_daily_units': round(avg_units, 1),
            'avg_daily_revenue': round(avg_revenue, 2),
            'days_sold': product['days_sold'],
            'trend_direction': trend_direction,
            'trend_percent': round(trend_percent, 1),
            'daily_history': daily_history
        })

    return product_trends


@tracer.capture_method
def build_trends_response(all_data: list, all_product_data: list, dates: list) -> dict:
    """
    Build time-series data structure optimized for frontend charts.
    """
    # Organize data by date and store
    by_date = {}
    stores = set()

    for record in all_data:
        date = record.get('date')
        store_id = record.get('store_id')
        stores.add(store_id)

        if date not in by_date:
            by_date[date] = {}
        by_date[date][store_id] = record

    stores = sorted(list(stores))

    # Build time series for charts
    time_series = []
    for date in dates:
        entry = {'date': date, 'total_sales': 0, 'total_transactions': 0}

        for store_id in stores:
            store_data = by_date.get(date, {}).get(store_id)
            if store_data:
                sales = store_data.get('total_sales', 0)
                transactions = store_data.get('transaction_count', 0)
                entry[f'{store_id}_sales'] = sales
                entry[f'{store_id}_transactions'] = transactions
                entry['total_sales'] += sales
                entry['total_transactions'] += transactions
            else:
                entry[f'{store_id}_sales'] = 0
                entry[f'{store_id}_transactions'] = 0

        entry['total_sales'] = round(entry['total_sales'], 2)
        time_series.append(entry)

    # Calculate store performance summaries
    store_summaries = []
    for store_id in stores:
        store_records = [r for r in all_data if r.get('store_id') == store_id]
        if store_records:
            # Sort by date for trend calculation
            store_records.sort(key=lambda x: x.get('date', ''))

            total_sales = sum(r.get('total_sales', 0) for r in store_records)
            total_transactions = sum(r.get('transaction_count', 0) for r in store_records)
            avg_daily_sales = total_sales / len(store_records)

            # Calculate trend (first vs last)
            if len(store_records) >= 2:
                first_sales = store_records[0].get('total_sales', 0)
                last_sales = store_records[-1].get('total_sales', 0)
                trend_pct = ((last_sales - first_sales) / first_sales * 100) if first_sales > 0 else 0
            else:
                trend_pct = 0

            store_summaries.append({
                'store_id': store_id,
                'total_sales': round(total_sales, 2),
                'total_transactions': total_transactions,
                'avg_daily_sales': round(avg_daily_sales, 2),
                'days_with_data': len(store_records),
                'trend_percent': round(trend_pct, 1)
            })

    # Sort by total sales descending
    store_summaries.sort(key=lambda x: x['total_sales'], reverse=True)

    # Build product trends
    product_trends = build_product_trends(all_product_data, dates)

    return {
        'stores': stores,
        'dates': dates,
        'time_series': time_series,
        'store_summaries': store_summaries,
        'product_trends': product_trends
    }


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
    store_filter = query_params.get('store_id')
    days = int(query_params.get('days', 30))

    # Get available dates
    available_dates = get_available_dates(table)

    if not available_dates:
        return cors_response(200, {
            'message': 'No data available',
            'stores': [],
            'dates': [],
            'time_series': [],
            'store_summaries': [],
            'product_trends': []
        })

    # Limit to requested number of days (most recent)
    target_dates = available_dates[-days:] if len(available_dates) > days else available_dates

    # Query data for each date (efficient GSI1 queries)
    all_data = []
    all_product_data = []
    for date in target_dates:
        date_data = query_date_data(table, date, store_filter)
        all_data.extend(date_data)

        product_data = query_products_for_date(table, date)
        all_product_data.extend(product_data)

    # Build response
    response_data = build_trends_response(all_data, all_product_data, target_dates)
    response_data['days_requested'] = days
    response_data['available_dates'] = available_dates

    logger.info("Trends response prepared", extra={
        "store_count": len(response_data['stores']),
        "date_count": len(target_dates),
        "record_count": len(all_data),
        "product_count": len(response_data['product_trends'])
    })

    return cors_response(200, response_data)
