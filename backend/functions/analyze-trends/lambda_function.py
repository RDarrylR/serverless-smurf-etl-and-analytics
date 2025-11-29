"""
Analyze Trends Lambda

Use Amazon Bedrock (Nova Lite) to analyze sales trends from store data
by comparing current day against historical data (last 7 days).

Input: { "date": "2025-01-15", "store_summaries": [...], "company_metrics": {...}, "product_metrics": [...] }
Output: { "date": "...", "trends": [...], "top_products_trend": [...] }
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
def get_historical_company_metrics(current_date: str) -> list:
    """
    Query DynamoDB for company-wide daily metrics over the past N days.
    Returns a list of daily company summaries.
    """
    table = dynamodb.Table(DYNAMODB_TABLE)

    current = datetime.strptime(current_date, '%Y-%m-%d')
    company_history = []

    for i in range(1, HISTORICAL_DAYS + 1):
        past_date = current - timedelta(days=i)
        date_str = past_date.strftime('%Y-%m-%d')

        try:
            # Query all stores for this date
            response = table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'DATE#{date_str}'
                }
            )

            items = response.get('Items', [])
            store_items = [item for item in items if item.get('GSI1SK', '').startswith('STORE#')]

            if store_items:
                total_sales = sum(float(item.get('total_sales', 0)) for item in store_items)
                total_transactions = sum(int(item.get('transaction_count', 0)) for item in store_items)

                company_history.append({
                    'date': date_str,
                    'total_sales': round(total_sales, 2),
                    'total_transactions': total_transactions,
                    'store_count': len(store_items),
                    'avg_transaction': round(total_sales / max(total_transactions, 1), 2)
                })

        except Exception as e:
            logger.warning(f"Error querying company metrics for {date_str}", extra={"error": str(e)})

    # Sort by date ascending
    company_history.sort(key=lambda x: x['date'])
    return company_history


@tracer.capture_method
def get_historical_product_data(current_date: str, product_skus: list) -> dict:
    """
    Query DynamoDB for historical data for each product over the past N days.
    Returns a dict with sku -> list of daily metrics.
    """
    table = dynamodb.Table(DYNAMODB_TABLE)

    current = datetime.strptime(current_date, '%Y-%m-%d')
    historical_dates = []
    for i in range(1, HISTORICAL_DAYS + 1):
        past_date = current - timedelta(days=i)
        historical_dates.append(past_date.strftime('%Y-%m-%d'))

    product_history = {sku: [] for sku in product_skus}

    # Query each product using GSI1 (PRODUCT#sku -> DATE#yyyy-mm-dd)
    for sku in product_skus:
        try:
            response = table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'PRODUCT#{sku}'
                }
            )

            for item in response.get('Items', []):
                gsi1sk = item.get('GSI1SK', '')
                if gsi1sk.startswith('DATE#'):
                    item_date = gsi1sk.replace('DATE#', '')
                    if item_date in historical_dates:
                        converted = decimal_to_float(item)
                        converted['date'] = item_date
                        product_history[sku].append(converted)

        except Exception as e:
            logger.warning(f"Error querying historical data for product {sku}", extra={"error": str(e)})

    return product_history


@tracer.capture_method
def calculate_trend_metrics(today_value: float, historical_values: list) -> dict:
    """Calculate trend metrics comparing today vs historical average."""
    if not historical_values:
        return {'avg': None, 'deviation_percent': None, 'trend_direction': 'unknown'}

    avg = sum(historical_values) / len(historical_values)
    if avg > 0:
        deviation = ((today_value - avg) / avg) * 100
    else:
        deviation = 0

    # Determine trend direction
    if len(historical_values) >= 2:
        recent = historical_values[-2:]  # Last 2 days
        earlier = historical_values[:-2] if len(historical_values) > 2 else historical_values[:1]
        recent_avg = sum(recent) / len(recent) if recent else 0
        earlier_avg = sum(earlier) / len(earlier) if earlier else 0

        if recent_avg > earlier_avg * 1.05:
            trend_direction = 'increasing'
        elif recent_avg < earlier_avg * 0.95:
            trend_direction = 'decreasing'
        else:
            trend_direction = 'stable'
    else:
        trend_direction = 'insufficient_data'

    return {
        'avg': round(avg, 2),
        'deviation_percent': round(deviation, 1),
        'trend_direction': trend_direction
    }


@tracer.capture_method
def build_top_products_trend(product_metrics: list, product_history: dict) -> list:
    """
    Build a summary of top selling products with historical trend data.
    Returns list of products with their trend information.
    """
    top_products_trend = []

    for product in product_metrics[:10]:  # Top 10 products
        sku = product.get('sku')
        name = product.get('name')
        today_units = product.get('units_sold', 0)
        today_revenue = product.get('revenue', 0)

        # Get historical data for this product
        hist_records = product_history.get(sku, [])
        hist_units = [r.get('units_sold', 0) for r in hist_records]
        hist_revenue = [r.get('revenue', 0) for r in hist_records]

        # Calculate trends
        units_trend = calculate_trend_metrics(today_units, hist_units)
        revenue_trend = calculate_trend_metrics(today_revenue, hist_revenue)

        # Build daily history for sparkline/chart data
        daily_history = []
        for record in sorted(hist_records, key=lambda x: x.get('date', '')):
            daily_history.append({
                'date': record.get('date'),
                'units_sold': record.get('units_sold', 0),
                'revenue': record.get('revenue', 0)
            })

        top_products_trend.append({
            'sku': sku,
            'name': name,
            'today_units_sold': today_units,
            'today_revenue': round(today_revenue, 2),
            'historical_avg_units': units_trend['avg'],
            'units_vs_history_percent': units_trend['deviation_percent'],
            'units_trend': units_trend['trend_direction'],
            'historical_avg_revenue': revenue_trend['avg'],
            'revenue_vs_history_percent': revenue_trend['deviation_percent'],
            'revenue_trend': revenue_trend['trend_direction'],
            'days_of_history': len(hist_records),
            'daily_history': daily_history,
            'stores_count': len(product.get('stores_sold_at', []))
        })

    return top_products_trend


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
def build_trends_prompt(date: str, store_summaries: list, company_metrics: dict,
                        product_metrics: list, store_historical: dict, company_history: list,
                        top_products_trend: list) -> str:
    """Build the prompt for trend analysis with historical context."""
    # Format store performance data with historical comparison
    store_performance = []
    for store in store_summaries:
        store_id = store.get('store_id')
        today_sales = store.get('total_sales', 0)
        today_transactions = store.get('transaction_count', 0)

        # Get historical data for this store
        hist_records = store_historical.get(store_id, [])
        hist_sales = [r.get('total_sales', 0) for r in hist_records]
        hist_transactions = [r.get('transaction_count', 0) for r in hist_records]

        sales_trend = calculate_trend_metrics(today_sales, hist_sales)
        trans_trend = calculate_trend_metrics(today_transactions, hist_transactions)

        store_performance.append({
            'store_id': store_id,
            'today_sales': today_sales,
            'today_transactions': today_transactions,
            'historical_avg_sales': sales_trend['avg'],
            'sales_vs_history_percent': sales_trend['deviation_percent'],
            'sales_trend': sales_trend['trend_direction'],
            'historical_avg_transactions': trans_trend['avg'],
            'transactions_vs_history_percent': trans_trend['deviation_percent'],
            'transactions_trend': trans_trend['trend_direction'],
            'days_of_history': len(hist_records),
            'top_products': store.get('top_products', [])[:3]
        })

    # Format product trend data for prompt (simplified view)
    product_trends_summary = []
    for p in top_products_trend[:10]:
        product_trends_summary.append({
            'sku': p['sku'],
            'name': p['name'],
            'today_units': p['today_units_sold'],
            'today_revenue': p['today_revenue'],
            'historical_avg_units': p['historical_avg_units'],
            'units_vs_history_percent': p['units_vs_history_percent'],
            'units_trend': p['units_trend'],
            'days_of_history': p['days_of_history']
        })

    # Calculate company-wide trends
    today_total_sales = company_metrics.get('total_sales', 0)
    hist_company_sales = [d['total_sales'] for d in company_history]
    company_sales_trend = calculate_trend_metrics(today_total_sales, hist_company_sales)

    today_total_trans = company_metrics.get('total_transactions', 0)
    hist_company_trans = [d['total_transactions'] for d in company_history]
    company_trans_trend = calculate_trend_metrics(today_total_trans, hist_company_trans)

    prompt = f"""Analyze the following sales data for {date} and identify notable trends by comparing against the last {HISTORICAL_DAYS} days of historical data.

TODAY'S COMPANY SUMMARY WITH HISTORICAL COMPARISON:
- Total Sales: ${company_metrics.get('total_sales', 0):,.2f}
- Historical Avg Sales: ${company_sales_trend['avg'] or 0:,.2f}
- Sales vs History: {company_sales_trend['deviation_percent'] or 'N/A'}%
- Sales Trend Direction: {company_sales_trend['trend_direction']}
- Total Transactions: {company_metrics.get('total_transactions', 0)}
- Historical Avg Transactions: {company_trans_trend['avg'] or 'N/A'}
- Transactions vs History: {company_trans_trend['deviation_percent'] or 'N/A'}%
- Stores Reporting: {company_metrics.get('store_count', 0)}/11
- Average Transaction: ${company_metrics.get('avg_transaction', 0):,.2f}

HISTORICAL COMPANY PERFORMANCE (Last {len(company_history)} days):
{json.dumps(company_history, indent=2)}

TOP PRODUCTS WITH HISTORICAL TRENDS:
{json.dumps(product_trends_summary, indent=2)}

STORE PERFORMANCE WITH HISTORICAL COMPARISON:
{json.dumps(store_performance, indent=2)}

PAYMENT BREAKDOWN TODAY:
{json.dumps(company_metrics.get('payment_breakdown', {}), indent=2)}

Identify trends in the following categories:
1. WEEK-OVER-WEEK TRENDS: How is overall performance trending compared to the past week?
2. STORE MOMENTUM: Which stores are showing consistent improvement or decline over time?
3. PRODUCT TRENDS: Which products are rising/falling in popularity? Identify hot sellers and declining products based on historical comparison.
4. SALES VELOCITY: Is the business accelerating, stable, or slowing?
5. PAYMENT PREFERENCES: Notable payment method usage patterns

IMPORTANT: Focus on HISTORICAL TRENDS and patterns over time, not just single-day observations.
Pay special attention to products showing significant changes vs their historical averages.

Return your analysis as a JSON object with this exact structure:
{{
  "trends": [
    {{
      "type": "week_over_week|store_momentum|product_trend|sales_velocity|payment_trend",
      "title": "Brief trend title",
      "description": "Detailed explanation including historical context",
      "affected_items": ["list", "of", "affected", "skus", "or", "store_ids"],
      "significance": "high|medium|low",
      "trend_direction": "improving|declining|stable",
      "metric_change_percent": 15.5
    }}
  ]
}}

Focus on actionable insights based on historical patterns. Return ONLY the JSON object, no other text."""

    return prompt


@tracer.capture_method
def parse_bedrock_response(response_text: str) -> list:
    """Parse the Bedrock response to extract trends."""
    try:
        # Try to find JSON in the response
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        result = json.loads(response_text)
        return result.get('trends', [])
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
    product_metrics = event.get('product_metrics', [])

    if not date:
        raise ValueError("Missing required field: date")

    if not store_summaries:
        logger.warning("No store summaries provided for trend analysis", extra={"date": date})
        return {
            'date': date,
            'trends': [],
            'top_products_trend': [],
            'message': 'No store data available for analysis'
        }

    # Get list of store IDs from today's data
    store_ids = [s.get('store_id') for s in store_summaries if s.get('store_id')]

    # Get list of product SKUs from today's data
    product_skus = [p.get('sku') for p in product_metrics[:10] if p.get('sku')]

    logger.info("Fetching historical data for trend analysis", extra={
        "date": date,
        "store_count": len(store_ids),
        "product_count": len(product_skus),
        "historical_days": HISTORICAL_DAYS
    })

    # Query historical data from DynamoDB
    store_historical = get_historical_data(date, store_ids)
    company_history = get_historical_company_metrics(date)
    product_history = get_historical_product_data(date, product_skus)

    # Build top products trend summary
    top_products_trend = build_top_products_trend(product_metrics, product_history)

    # Count stores with sufficient history
    stores_with_history = sum(1 for records in store_historical.values() if len(records) >= 3)
    products_with_history = sum(1 for records in product_history.values() if len(records) >= 1)

    logger.info("Analyzing trends with historical context", extra={
        "date": date,
        "store_count": len(store_summaries),
        "product_count": len(product_metrics),
        "stores_with_history": stores_with_history,
        "products_with_history": products_with_history,
        "days_of_company_history": len(company_history),
        "model_id": BEDROCK_MODEL_ID
    })

    # Build and send prompt to Bedrock
    prompt = build_trends_prompt(date, store_summaries, company_metrics,
                                  product_metrics, store_historical, company_history,
                                  top_products_trend)

    try:
        bedrock_result = invoke_bedrock(prompt)
        trends = parse_bedrock_response(bedrock_result['text'])

        metrics.add_metric(name="TrendsIdentified", unit=MetricUnit.Count, value=len(trends))
        metrics.add_metric(name="BedrockInvocations", unit=MetricUnit.Count, value=1)
        metrics.add_dimension(name="ModelId", value=BEDROCK_MODEL_ID)

        # Log token usage as metrics if available
        usage = bedrock_result.get('usage', {})
        if usage.get('inputTokens'):
            metrics.add_metric(name="BedrockInputTokens", unit=MetricUnit.Count, value=usage['inputTokens'])
        if usage.get('outputTokens'):
            metrics.add_metric(name="BedrockOutputTokens", unit=MetricUnit.Count, value=usage['outputTokens'])

        logger.info("Trend analysis complete", extra={
            "date": date,
            "trend_count": len(trends),
            "stores_with_history": stores_with_history,
            "products_with_history": products_with_history,
            "input_tokens": usage.get('inputTokens'),
            "output_tokens": usage.get('outputTokens')
        })

        return {
            'date': date,
            'trends': trends,
            'trend_count': len(trends),
            'top_products_trend': top_products_trend,
            'historical_days_used': HISTORICAL_DAYS,
            'stores_with_history': stores_with_history,
            'products_with_history': products_with_history
        }

    except Exception as e:
        logger.exception("Error invoking Bedrock for trend analysis")
        metrics.add_metric(name="BedrockErrors", unit=MetricUnit.Count, value=1)
        raise
