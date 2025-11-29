"""
Combine Insights Lambda

Combine outputs from anomaly detection, trend analysis, and recommendations.
Also writes insights to DynamoDB and handles partial failures from Bedrock tasks.

Input: {
    "date": "2025-01-15",
    "anomalies_result": {...} | null,
    "trends_result": {...} | null,
    "recommendations_result": {...} | null,
    "company_metrics": {...}
}
Output: { "date": "...", "insights": {...}, "has_errors": bool }
"""

import boto3
import json
import os
import uuid
from decimal import Decimal

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb = boto3.resource('dynamodb')


@tracer.capture_method
def write_insights_to_dynamodb(table, date: str, insights: dict):
    """Write combined insights to DynamoDB."""
    # Write anomalies
    for anomaly in insights.get('anomalies', []):
        insight_id = str(uuid.uuid4())[:8]
        item = {
            'PK': f'DATE#{date}',
            'SK': f'INSIGHT#ANOMALY#{insight_id}',
            'GSI1PK': f'INSIGHT#anomaly',
            'GSI1SK': f'DATE#{date}',
            'insight_type': 'anomaly',
            'severity': anomaly.get('severity', 'info'),
            'store_id': anomaly.get('store_id'),
            'title': anomaly.get('title'),
            'description': anomaly.get('description'),
            'metric_value': Decimal(str(anomaly.get('metric_value', 0))) if anomaly.get('metric_value') else None,
            'deviation_percent': Decimal(str(anomaly.get('deviation_percent', 0))) if anomaly.get('deviation_percent') else None
        }
        # Remove None values
        item = {k: v for k, v in item.items() if v is not None}
        table.put_item(Item=item)

    # Write trends
    for trend in insights.get('trends', []):
        insight_id = str(uuid.uuid4())[:8]
        item = {
            'PK': f'DATE#{date}',
            'SK': f'INSIGHT#TREND#{insight_id}',
            'GSI1PK': f'INSIGHT#trend',
            'GSI1SK': f'DATE#{date}',
            'insight_type': 'trend',
            'trend_type': trend.get('type'),
            'title': trend.get('title'),
            'description': trend.get('description'),
            'significance': trend.get('significance', 'medium'),
            'affected_items': trend.get('affected_items', [])
        }
        table.put_item(Item=item)

    # Write recommendations
    for rec in insights.get('recommendations', []):
        insight_id = str(uuid.uuid4())[:8]
        item = {
            'PK': f'DATE#{date}',
            'SK': f'INSIGHT#RECOMMENDATION#{insight_id}',
            'GSI1PK': f'INSIGHT#recommendation',
            'GSI1SK': f'DATE#{date}',
            'insight_type': 'recommendation',
            'priority': rec.get('priority', 'medium'),
            'category': rec.get('category'),
            'title': rec.get('title'),
            'description': rec.get('description'),
            'affected_stores': rec.get('affected_stores', []),
            'affected_products': rec.get('affected_products', []),
            'expected_impact': rec.get('expected_impact')
        }
        # Remove None values
        item = {k: v for k, v in item.items() if v is not None}
        table.put_item(Item=item)

    logger.debug("Wrote insights to DynamoDB", extra={
        "anomaly_count": len(insights.get('anomalies', [])),
        "trend_count": len(insights.get('trends', [])),
        "recommendation_count": len(insights.get('recommendations', []))
    })


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    table_name = os.environ.get('DYNAMODB_TABLE', 'SalesData')
    table = dynamodb.Table(table_name)

    date = event.get('date')
    company_metrics = event.get('company_metrics', {})

    if not date:
        raise ValueError("Missing required field: date")

    # Extract results from parallel Bedrock tasks
    # These may be None if a task failed after retries
    anomalies_result = event.get('anomalies_result')
    trends_result = event.get('trends_result')
    recommendations_result = event.get('recommendations_result')

    # Track which analyses succeeded
    errors = []
    insights = {
        'anomalies': [],
        'trends': [],
        'recommendations': []
    }

    # Process anomalies
    if anomalies_result and 'anomalies' in anomalies_result:
        insights['anomalies'] = anomalies_result.get('anomalies', [])
        logger.info("Anomalies received", extra={"count": len(insights['anomalies'])})
    elif anomalies_result and 'error' in anomalies_result:
        errors.append({
            'task': 'detect-anomalies',
            'error': anomalies_result.get('error', 'Unknown error')
        })
        logger.warning("Anomaly detection failed", extra={"error": anomalies_result.get('error')})
    else:
        logger.info("No anomaly results provided")

    # Process trends
    if trends_result and 'trends' in trends_result:
        insights['trends'] = trends_result.get('trends', [])
        logger.info("Trends received", extra={"count": len(insights['trends'])})
    elif trends_result and 'error' in trends_result:
        errors.append({
            'task': 'analyze-trends',
            'error': trends_result.get('error', 'Unknown error')
        })
        logger.warning("Trend analysis failed", extra={"error": trends_result.get('error')})
    else:
        logger.info("No trend results provided")

    # Process recommendations
    if recommendations_result and 'recommendations' in recommendations_result:
        insights['recommendations'] = recommendations_result.get('recommendations', [])
        logger.info("Recommendations received", extra={"count": len(insights['recommendations'])})
    elif recommendations_result and 'error' in recommendations_result:
        errors.append({
            'task': 'generate-recommendations',
            'error': recommendations_result.get('error', 'Unknown error')
        })
        logger.warning("Recommendation generation failed", extra={"error": recommendations_result.get('error')})
    else:
        logger.info("No recommendation results provided")

    # Write insights to DynamoDB
    total_insights = (
        len(insights['anomalies']) +
        len(insights['trends']) +
        len(insights['recommendations'])
    )

    if total_insights > 0:
        write_insights_to_dynamodb(table, date, insights)

    # Record metrics
    metrics.add_metric(name="InsightsCombined", unit=MetricUnit.Count, value=total_insights)
    metrics.add_metric(name="AnomaliesStored", unit=MetricUnit.Count, value=len(insights['anomalies']))
    metrics.add_metric(name="TrendsStored", unit=MetricUnit.Count, value=len(insights['trends']))
    metrics.add_metric(name="RecommendationsStored", unit=MetricUnit.Count, value=len(insights['recommendations']))

    if errors:
        metrics.add_metric(name="BedrockTaskFailures", unit=MetricUnit.Count, value=len(errors))

    has_errors = len(errors) > 0

    logger.info("Insights combined", extra={
        "date": date,
        "total_insights": total_insights,
        "has_errors": has_errors,
        "error_count": len(errors)
    })

    return {
        'date': date,
        'insights': insights,
        'summary': {
            'anomaly_count': len(insights['anomalies']),
            'trend_count': len(insights['trends']),
            'recommendation_count': len(insights['recommendations']),
            'total_insights': total_insights
        },
        'has_errors': has_errors,
        'errors': errors if errors else None,
        'company_metrics': company_metrics  # Pass through for report generation
    }
