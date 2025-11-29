"""
Detect Anomalies Lambda

Use Amazon Bedrock (Nova Lite) to analyze store sales data and identify anomalies
by comparing today's metrics against historical averages (last 7 days).

Input: { "date": "2025-01-15", "store_summaries": [...], "company_metrics": {...} }
Output: { "date": "...", "anomalies": [...] }
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

bedrock_runtime = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-lite-v1:0')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'SalesData')
HISTORICAL_DAYS = 7  # Number of days to look back for historical comparison

# Bedrock pricing per 1000 tokens (USD) - Nova Lite on-demand pricing
BEDROCK_PRICING = {
    'amazon.nova-lite-v1:0': {'input': 0.00006, 'output': 0.00024},
    'amazon.nova-micro-v1:0': {'input': 0.000035, 'output': 0.00014},
    'amazon.nova-pro-v1:0': {'input': 0.0008, 'output': 0.0032},
}


def decimal_to_float(obj):
    """Recursively convert Decimal to float in nested structures."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Calculate estimated cost for a Bedrock invocation."""
    pricing = BEDROCK_PRICING.get(model_id, {'input': 0, 'output': 0})
    input_cost = (input_tokens / 1000) * pricing['input']
    output_cost = (output_tokens / 1000) * pricing['output']
    total_cost = input_cost + output_cost
    return {
        'input_cost_usd': round(input_cost, 8),
        'output_cost_usd': round(output_cost, 8),
        'total_cost_usd': round(total_cost, 8)
    }


@tracer.capture_method
def get_historical_data(current_date: str, store_ids: list) -> dict:
    """
    Query DynamoDB for historical data for each store over the past N days.
    Returns a dict with store_id -> list of daily metrics.
    """
    table = dynamodb.Table(DYNAMODB_TABLE)

    # Calculate date range (excluding current date)
    current = datetime.strptime(current_date, '%Y-%m-%d')
    historical_dates = []
    for i in range(1, HISTORICAL_DAYS + 1):
        past_date = current - timedelta(days=i)
        historical_dates.append(past_date.strftime('%Y-%m-%d'))

    historical_data = {store_id: [] for store_id in store_ids}

    # Query each date using GSI1 (DATE#yyyy-mm-dd -> STORE#xxxx)
    for date_str in historical_dates:
        try:
            response = table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'DATE#{date_str}'
                }
            )

            for item in response.get('Items', []):
                gsi1sk = item.get('GSI1SK', '')
                if gsi1sk.startswith('STORE#'):
                    store_id = gsi1sk.replace('STORE#', '')
                    if store_id in historical_data:
                        converted = decimal_to_float(item)
                        converted['date'] = date_str
                        historical_data[store_id].append(converted)

        except Exception as e:
            logger.warning(f"Error querying historical data for {date_str}", extra={"error": str(e)})

    return historical_data


@tracer.capture_method
def calculate_store_historical_averages(historical_data: dict) -> dict:
    """
    Calculate historical averages for each store.
    Returns dict with store_id -> { avg_sales, avg_transactions, days_of_data }
    """
    store_averages = {}

    for store_id, daily_records in historical_data.items():
        if not daily_records:
            store_averages[store_id] = {
                'avg_sales': None,
                'avg_transactions': None,
                'days_of_data': 0
            }
            continue

        total_sales = sum(r.get('total_sales', 0) for r in daily_records)
        total_transactions = sum(r.get('transaction_count', 0) for r in daily_records)
        days = len(daily_records)

        store_averages[store_id] = {
            'avg_sales': round(total_sales / days, 2),
            'avg_transactions': round(total_transactions / days, 1),
            'days_of_data': days,
            'daily_sales': [r.get('total_sales', 0) for r in daily_records]
        }

    return store_averages


@tracer.capture_method
def invoke_bedrock(prompt: str) -> dict:
    """Invoke Amazon Bedrock with the given prompt."""
    body = {
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        "inferenceConfig": {
            "maxTokens": 2048,
            "temperature": 0.3,
            "topP": 0.9
        }
    }

    logger.debug("Sending prompt to Bedrock", extra={
        "model_id": BEDROCK_MODEL_ID,
        "prompt_length": len(prompt),
        "prompt": prompt
    })

    response = bedrock_runtime.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )

    response_body = json.loads(response['body'].read())

    # Extract usage metrics if available
    usage = response_body.get('usage', {})
    response_text = response_body['output']['message']['content'][0]['text']

    # Calculate estimated cost
    input_tokens = usage.get('inputTokens', 0)
    output_tokens = usage.get('outputTokens', 0)
    cost = calculate_cost(BEDROCK_MODEL_ID, input_tokens, output_tokens)

    logger.debug("Received response from Bedrock", extra={
        "model_id": BEDROCK_MODEL_ID,
        "response_length": len(response_text),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": usage.get('totalTokens'),
        "estimated_cost_usd": cost['total_cost_usd'],
        "cost_breakdown": cost,
        "response": response_text
    })

    return {
        'text': response_text,
        'usage': usage,
        'cost': cost
    }


@tracer.capture_method
def build_anomaly_prompt(date: str, store_summaries: list, company_metrics: dict, store_historical: dict) -> str:
    """Build the prompt for anomaly detection with historical context."""
    # Format store data with historical comparison
    store_data = []
    for store in store_summaries:
        store_id = store.get('store_id')
        today_sales = store.get('total_sales', 0)
        today_transactions = store.get('transaction_count', 0)

        historical = store_historical.get(store_id, {})
        hist_avg_sales = historical.get('avg_sales')
        hist_avg_transactions = historical.get('avg_transactions')
        days_of_history = historical.get('days_of_data', 0)

        # Calculate deviation from historical average
        sales_deviation = None
        if hist_avg_sales and hist_avg_sales > 0:
            sales_deviation = round(((today_sales - hist_avg_sales) / hist_avg_sales) * 100, 1)

        trans_deviation = None
        if hist_avg_transactions and hist_avg_transactions > 0:
            trans_deviation = round(((today_transactions - hist_avg_transactions) / hist_avg_transactions) * 100, 1)

        store_data.append({
            'store_id': store_id,
            'today_sales': today_sales,
            'today_transactions': today_transactions,
            'avg_transaction': round(today_sales / max(today_transactions, 1), 2),
            'historical_avg_sales': hist_avg_sales,
            'historical_avg_transactions': hist_avg_transactions,
            'sales_vs_history_percent': sales_deviation,
            'transactions_vs_history_percent': trans_deviation,
            'days_of_historical_data': days_of_history
        })

    prompt = f"""Analyze the following store sales data for {date} and identify anomalies by comparing today's performance against the last {HISTORICAL_DAYS} days.

TODAY'S STORE DATA WITH HISTORICAL COMPARISON:
{json.dumps(store_data, indent=2)}

TODAY'S COMPANY TOTALS:
- Total Sales: ${company_metrics.get('total_sales', 0):,.2f}
- Total Transactions: {company_metrics.get('total_transactions', 0)}
- Stores Reporting: {company_metrics.get('store_count', 0)}
- Average Transaction: ${company_metrics.get('avg_transaction', 0):,.2f}

Identify anomalies in the following categories:
1. HISTORICAL DEVIATION: Stores performing significantly different from their own historical average (>25% deviation)
2. SUDDEN CHANGES: Dramatic increases or decreases compared to recent history
3. PEER COMPARISON: Stores significantly under/over-performing compared to other stores today
4. CONSISTENCY ISSUES: Stores with erratic patterns (if historical data shows high variance)

IMPORTANT: Focus on deviations FROM HISTORICAL AVERAGES, not just peer comparison.

Return your analysis as a JSON object with this exact structure:
{{
  "anomalies": [
    {{
      "type": "historical_low|historical_high|sudden_drop|sudden_spike|peer_outlier",
      "severity": "info|warning|critical",
      "store_id": "0001",
      "title": "Brief description",
      "description": "Detailed explanation including historical context",
      "metric_value": 1234.56,
      "historical_average": 2000.00,
      "deviation_percent": -38.3
    }}
  ]
}}

Severity guide:
- critical: >50% deviation from historical average OR sudden complete drop
- warning: 25-50% deviation from historical average
- info: Notable but not concerning patterns

Only include actual anomalies. If no anomalies found, return an empty anomalies array.
Return ONLY the JSON object, no other text."""

    return prompt


@tracer.capture_method
def parse_bedrock_response(response_text: str) -> list:
    """Parse the Bedrock response to extract anomalies."""
    try:
        # Try to find JSON in the response
        # Sometimes models wrap JSON in markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        result = json.loads(response_text)
        return result.get('anomalies', [])
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse Bedrock response as JSON", extra={
            "error": str(e),
            "response_preview": response_text[:500]
        })
        return []


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    date = event.get('date')
    store_summaries = event.get('store_summaries', [])
    company_metrics = event.get('company_metrics', {})

    if not date:
        raise ValueError("Missing required field: date")

    if not store_summaries:
        logger.warning("No store summaries provided for anomaly detection", extra={"date": date})
        return {
            'date': date,
            'anomalies': [],
            'message': 'No store data available for analysis'
        }

    # Get list of store IDs from today's data
    store_ids = [s.get('store_id') for s in store_summaries if s.get('store_id')]

    logger.info("Fetching historical data for anomaly detection", extra={
        "date": date,
        "store_count": len(store_ids),
        "historical_days": HISTORICAL_DAYS
    })

    # Query historical data from DynamoDB
    historical_data = get_historical_data(date, store_ids)

    # Calculate historical averages per store
    store_historical = calculate_store_historical_averages(historical_data)

    # Count stores with sufficient history (need at least 3 days for meaningful comparison)
    stores_with_history = sum(1 for s in store_historical.values() if s.get('days_of_data', 0) >= 3)

    logger.info("Historical data summary", extra={
        "date": date,
        "store_count": len(store_summaries),
        "stores_with_history": stores_with_history,
        "historical_days": HISTORICAL_DAYS
    })

    # Skip anomaly detection if insufficient historical data
    if stores_with_history == 0:
        logger.info("Skipping anomaly detection - no stores have sufficient historical data", extra={
            "date": date,
            "store_count": len(store_summaries),
            "minimum_days_required": 3
        })
        return {
            'date': date,
            'anomalies': [],
            'anomaly_count': 0,
            'historical_days_used': HISTORICAL_DAYS,
            'stores_with_history': 0,
            'message': 'Insufficient historical data for anomaly detection (need at least 3 days)'
        }

    logger.info("Detecting anomalies with historical context", extra={
        "date": date,
        "store_count": len(store_summaries),
        "stores_with_history": stores_with_history,
        "model_id": BEDROCK_MODEL_ID
    })

    # Build and send prompt to Bedrock
    prompt = build_anomaly_prompt(date, store_summaries, company_metrics, store_historical)

    try:
        bedrock_result = invoke_bedrock(prompt)
        anomalies = parse_bedrock_response(bedrock_result['text'])

        metrics.add_metric(name="AnomaliesDetected", unit=MetricUnit.Count, value=len(anomalies))
        metrics.add_metric(name="BedrockInvocations", unit=MetricUnit.Count, value=1)
        metrics.add_dimension(name="ModelId", value=BEDROCK_MODEL_ID)

        # Log token usage as metrics if available
        usage = bedrock_result.get('usage', {})
        if usage.get('inputTokens'):
            metrics.add_metric(name="BedrockInputTokens", unit=MetricUnit.Count, value=usage['inputTokens'])
        if usage.get('outputTokens'):
            metrics.add_metric(name="BedrockOutputTokens", unit=MetricUnit.Count, value=usage['outputTokens'])

        logger.info("Anomaly detection complete", extra={
            "date": date,
            "anomaly_count": len(anomalies),
            "stores_with_history": stores_with_history,
            "input_tokens": usage.get('inputTokens'),
            "output_tokens": usage.get('outputTokens')
        })

        return {
            'date': date,
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'historical_days_used': HISTORICAL_DAYS,
            'stores_with_history': stores_with_history
        }

    except Exception as e:
        logger.exception("Error invoking Bedrock for anomaly detection")
        metrics.add_metric(name="BedrockErrors", unit=MetricUnit.Count, value=1)
        raise
