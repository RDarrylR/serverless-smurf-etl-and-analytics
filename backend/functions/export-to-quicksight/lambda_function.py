"""
Export to QuickSight Lambda

Export DynamoDB data to S3 as JSON files for QuickSight consumption.
Queries last N days of store summaries, product metrics, and insights,
then writes them to S3 in a format optimized for QuickSight.

Input: { "days": 30, "date": "2025-01-15" }  (date is optional, defaults to today)
Output: { "exported_files": [...], "record_counts": {...} }
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

import awswrangler as wr
import pandas as pd

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def decimal_to_float(obj):
    """Recursively convert Decimal to float in nested structures."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


@tracer.capture_method
def query_store_summaries(table, start_date: str, end_date: str) -> list:
    """Query store summaries from DynamoDB using GSI1."""
    all_items = []

    # Generate list of dates to query
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    current = start

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')

        # Query using GSI1 to get all stores for this date
        response = table.query(
            IndexName='GSI1',
            KeyConditionExpression='GSI1PK = :pk',
            ExpressionAttributeValues={
                ':pk': f'DATE#{date_str}'
            }
        )

        for item in response.get('Items', []):
            # Only include store summaries, not other record types
            # GSI1SK contains STORE#xxx when querying via GSI1
            if item.get('GSI1SK', '').startswith('STORE#'):
                all_items.append(decimal_to_float(item))

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
                    all_items.append(decimal_to_float(item))

        current += timedelta(days=1)

    logger.info("Queried store summaries", extra={
        "record_count": len(all_items),
        "start_date": start_date,
        "end_date": end_date
    })

    return all_items


@tracer.capture_method
def query_insights(table, start_date: str, end_date: str) -> dict:
    """Query insights from DynamoDB."""
    anomalies = []
    trends = []
    recommendations = []

    # Generate list of dates to query
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    current = start

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')

        # Query all insights for this date
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

        current += timedelta(days=1)

    logger.info("Queried insights", extra={
        "anomaly_count": len(anomalies),
        "trend_count": len(trends),
        "recommendation_count": len(recommendations),
        "start_date": start_date,
        "end_date": end_date
    })

    return {
        'anomalies': anomalies,
        'trends': trends,
        'recommendations': recommendations
    }


@tracer.capture_method
def create_store_summaries_df(store_summaries: list) -> pd.DataFrame:
    """Convert store summaries to a flat DataFrame for QuickSight."""
    if not store_summaries:
        return pd.DataFrame()

    rows = []
    for summary in store_summaries:
        row = {
            'date': summary.get('date'),
            'store_id': summary.get('store_id'),
            'year': summary.get('year'),
            'month': summary.get('month'),
            'day': summary.get('day'),
            'total_sales': summary.get('total_sales', 0),
            'total_discount': summary.get('total_discount', 0),
            'net_sales': summary.get('net_sales', 0),
            'transaction_count': summary.get('transaction_count', 0),
            'item_count': summary.get('item_count', 0),
            'avg_transaction': summary.get('avg_transaction', 0),
            'record_count': summary.get('record_count', 0),
            'created_at': summary.get('created_at')
        }

        # Add payment breakdown as separate columns
        payment = summary.get('payment_breakdown', {})
        row['payment_cash'] = payment.get('cash', 0)
        row['payment_credit'] = payment.get('credit', 0)
        row['payment_debit'] = payment.get('debit', 0)
        row['payment_gift_card'] = payment.get('gift_card', 0)

        rows.append(row)

    df = pd.DataFrame(rows)

    # Keep date as string in YYYY-MM-DD format for QuickSight date filtering
    # (pd.to_datetime adds timestamp which causes issues with date-only filters)

    return df


@tracer.capture_method
def create_top_products_df(store_summaries: list) -> pd.DataFrame:
    """Extract top products from store summaries into a separate DataFrame."""
    if not store_summaries:
        return pd.DataFrame()

    rows = []
    for summary in store_summaries:
        date = summary.get('date')
        store_id = summary.get('store_id')

        for product in summary.get('top_products', []):
            rows.append({
                'date': date,
                'store_id': store_id,
                'sku': product.get('sku'),
                'name': product.get('name'),
                'units_sold': product.get('units', 0),
                'revenue': product.get('revenue', 0)
            })

    df = pd.DataFrame(rows)

    # Keep date as string in YYYY-MM-DD format for QuickSight date filtering

    return df


@tracer.capture_method
def create_anomalies_df(anomalies: list) -> pd.DataFrame:
    """Convert anomalies to DataFrame."""
    if not anomalies:
        return pd.DataFrame()

    rows = []
    for anomaly in anomalies:
        rows.append({
            'date': anomaly.get('date'),
            'store_id': anomaly.get('store_id'),
            'severity': anomaly.get('severity'),
            'title': anomaly.get('title'),
            'description': anomaly.get('description'),
            'metric_value': anomaly.get('metric_value'),
            'deviation_percent': anomaly.get('deviation_percent')
        })

    df = pd.DataFrame(rows)

    # Keep date as string in YYYY-MM-DD format for QuickSight date filtering

    return df


@tracer.capture_method
def create_trends_df(trends: list) -> pd.DataFrame:
    """Convert trends to DataFrame."""
    if not trends:
        return pd.DataFrame()

    rows = []
    for trend in trends:
        # Convert affected_items list to comma-separated string for QuickSight
        affected_items = trend.get('affected_items', [])
        affected_items_str = ', '.join(affected_items) if affected_items else ''

        rows.append({
            'date': trend.get('date'),
            'trend_type': trend.get('trend_type'),
            'significance': trend.get('significance'),
            'title': trend.get('title'),
            'description': trend.get('description'),
            'affected_items': affected_items_str
        })

    df = pd.DataFrame(rows)

    # Keep date as string in YYYY-MM-DD format for QuickSight date filtering

    return df


@tracer.capture_method
def create_recommendations_df(recommendations: list) -> pd.DataFrame:
    """Convert recommendations to DataFrame."""
    if not recommendations:
        return pd.DataFrame()

    rows = []
    for rec in recommendations:
        affected_stores = rec.get('affected_stores', [])
        affected_products = rec.get('affected_products', [])

        rows.append({
            'date': rec.get('date'),
            'priority': rec.get('priority'),
            'category': rec.get('category'),
            'title': rec.get('title'),
            'description': rec.get('description'),
            'affected_stores': ', '.join(affected_stores) if affected_stores else '',
            'affected_products': ', '.join(affected_products) if affected_products else '',
            'expected_impact': rec.get('expected_impact')
        })

    df = pd.DataFrame(rows)

    # Keep date as string in YYYY-MM-DD format for QuickSight date filtering

    return df


@tracer.capture_method
def write_json_to_s3(df: pd.DataFrame, bucket: str, key: str) -> str:
    """Write DataFrame to S3 as JSON Lines (one JSON object per line) for QuickSight."""
    if df.empty:
        logger.info("Empty DataFrame, skipping write", extra={"key": key})
        return None

    s3_path = f's3://{bucket}/{key}'

    # Convert datetime columns to ISO format strings for JSON
    df_copy = df.copy()
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%dT%H:%M:%S')

    # Write as JSON Lines (each row is a separate JSON object on its own line)
    wr.s3.to_json(
        df=df_copy,
        path=s3_path,
        orient='records',
        lines=True,
        date_format='iso'
    )

    logger.info("Wrote JSON to S3", extra={
        "path": s3_path,
        "row_count": len(df)
    })

    return s3_path


@tracer.capture_method
def write_manifest(bucket: str, prefix: str, files: list) -> str:
    """Write a QuickSight manifest file pointing to the data files."""
    manifest = {
        "fileLocations": [
            {"URIs": files}
        ],
        "globalUploadSettings": {
            "format": "JSON"
        }
    }

    manifest_key = f'{prefix}/manifest.json'
    s3_client.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json'
    )

    logger.info("Wrote manifest file", extra={
        "key": manifest_key,
        "file_count": len(files)
    })

    return f's3://{bucket}/{manifest_key}'


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    table_name = os.environ.get('DYNAMODB_TABLE', 'SalesData')
    bucket_name = os.environ.get('S3_BUCKET')

    if not bucket_name:
        raise ValueError("S3_BUCKET environment variable is required")

    table = dynamodb.Table(table_name)

    # Get parameters
    days = event.get('days', 30)
    end_date_str = event.get('date')

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = datetime.utcnow()

    start_date = end_date - timedelta(days=days - 1)

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    logger.info("Starting QuickSight export", extra={
        "start_date": start_date_str,
        "end_date": end_date_str,
        "days": days,
        "bucket": bucket_name
    })

    # Query data from DynamoDB
    store_summaries = query_store_summaries(table, start_date_str, end_date_str)
    insights = query_insights(table, start_date_str, end_date_str)

    # Create DataFrames
    store_df = create_store_summaries_df(store_summaries)
    products_df = create_top_products_df(store_summaries)
    anomalies_df = create_anomalies_df(insights['anomalies'])
    trends_df = create_trends_df(insights['trends'])
    recommendations_df = create_recommendations_df(insights['recommendations'])

    # Export timestamp for file naming
    export_timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    prefix = 'quicksight'

    # Write to S3
    exported_files = []
    record_counts = {}

    # Store summaries
    if not store_df.empty:
        path = write_json_to_s3(
            store_df,
            bucket_name,
            f'{prefix}/store_summaries/store_summaries_{export_timestamp}.json'
        )
        if path:
            exported_files.append(path)
            record_counts['store_summaries'] = len(store_df)

    # Top products
    if not products_df.empty:
        path = write_json_to_s3(
            products_df,
            bucket_name,
            f'{prefix}/top_products/top_products_{export_timestamp}.json'
        )
        if path:
            exported_files.append(path)
            record_counts['top_products'] = len(products_df)

    # Anomalies
    if not anomalies_df.empty:
        path = write_json_to_s3(
            anomalies_df,
            bucket_name,
            f'{prefix}/anomalies/anomalies_{export_timestamp}.json'
        )
        if path:
            exported_files.append(path)
            record_counts['anomalies'] = len(anomalies_df)

    # Trends
    if not trends_df.empty:
        path = write_json_to_s3(
            trends_df,
            bucket_name,
            f'{prefix}/trends/trends_{export_timestamp}.json'
        )
        if path:
            exported_files.append(path)
            record_counts['trends'] = len(trends_df)

    # Recommendations
    if not recommendations_df.empty:
        path = write_json_to_s3(
            recommendations_df,
            bucket_name,
            f'{prefix}/recommendations/recommendations_{export_timestamp}.json'
        )
        if path:
            exported_files.append(path)
            record_counts['recommendations'] = len(recommendations_df)

    # Write manifest files for each dataset type (for easier QuickSight setup)
    manifests = {}
    for dataset_type in ['store_summaries', 'top_products', 'anomalies', 'trends', 'recommendations']:
        dataset_files = [f for f in exported_files if dataset_type in f]
        if dataset_files:
            manifest_path = write_manifest(
                bucket_name,
                f'{prefix}/{dataset_type}',
                dataset_files
            )
            manifests[dataset_type] = manifest_path

    # Record metrics
    metrics.add_metric(name="FilesExported", unit=MetricUnit.Count, value=len(exported_files))
    metrics.add_metric(name="StoreSummariesExported", unit=MetricUnit.Count, value=record_counts.get('store_summaries', 0))
    metrics.add_metric(name="ProductsExported", unit=MetricUnit.Count, value=record_counts.get('top_products', 0))
    metrics.add_metric(name="InsightsExported", unit=MetricUnit.Count, value=sum([
        record_counts.get('anomalies', 0),
        record_counts.get('trends', 0),
        record_counts.get('recommendations', 0)
    ]))

    result = {
        'export_date': end_date_str,
        'date_range': {
            'start': start_date_str,
            'end': end_date_str,
            'days': days
        },
        'exported_files': exported_files,
        'manifests': manifests,
        'record_counts': record_counts,
        'total_records': sum(record_counts.values())
    }

    logger.info("QuickSight export complete", extra=result)

    return result
