"""
Generate Recommendations Lambda

Use Amazon Bedrock (Nova Lite) to generate actionable recommendations based on anomalies and trends.

Input: { "date": "2025-01-15", "anomalies": [...], "trends": [...], "company_metrics": {...} }
Output: { "date": "...", "recommendations": [...] }
"""

import boto3
import json
import os

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

bedrock_runtime = boto3.client('bedrock-runtime')

BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-lite-v1:0')

# Bedrock pricing per 1000 tokens (USD) - Nova Lite on-demand pricing
BEDROCK_PRICING = {
    'amazon.nova-lite-v1:0': {'input': 0.00006, 'output': 0.00024},
    'amazon.nova-micro-v1:0': {'input': 0.000035, 'output': 0.00014},
    'amazon.nova-pro-v1:0': {'input': 0.0008, 'output': 0.0032},
}


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
            "temperature": 0.4,
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
def build_recommendations_prompt(date: str, anomalies: list, trends: list, company_metrics: dict) -> str:
    """Build the prompt for generating recommendations."""
    prompt = f"""Based on the following sales analysis for {date}, generate actionable business recommendations.

COMPANY PERFORMANCE SUMMARY:
- Total Sales: ${company_metrics.get('total_sales', 0):,.2f}
- Total Transactions: {company_metrics.get('total_transactions', 0)}
- Stores Reporting: {company_metrics.get('store_count', 0)}/11
- Best Store: #{company_metrics.get('best_store', {}).get('store_id', 'N/A')} (${company_metrics.get('best_store', {}).get('total_sales', 0):,.2f})
- Worst Store: #{company_metrics.get('worst_store', {}).get('store_id', 'N/A')} (${company_metrics.get('worst_store', {}).get('total_sales', 0):,.2f})

DETECTED ANOMALIES:
{json.dumps(anomalies, indent=2) if anomalies else "No anomalies detected"}

IDENTIFIED TRENDS:
{json.dumps(trends, indent=2) if trends else "No specific trends identified"}

Based on this analysis, generate specific, actionable recommendations for:
1. INVENTORY: Stock level adjustments based on product performance
2. MARKETING: Promotional opportunities based on trends
3. OPERATIONS: Store-specific actions for underperforming locations
4. STRATEGY: Longer-term strategic considerations

Return your recommendations as a JSON object with this exact structure:
{{
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "category": "inventory|marketing|operations|strategy",
      "title": "Brief recommendation title",
      "description": "Detailed explanation with specific actions",
      "affected_stores": ["0001", "0002"],
      "affected_products": ["SKU-001", "SKU-002"],
      "expected_impact": "Brief description of expected outcome"
    }}
  ]
}}

Prioritize high-impact, immediately actionable recommendations. Return ONLY the JSON object, no other text."""

    return prompt


@tracer.capture_method
def parse_bedrock_response(response_text: str) -> list:
    """Parse the Bedrock response to extract recommendations."""
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
        return result.get('recommendations', [])
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
    anomalies = event.get('anomalies', [])
    trends = event.get('trends', [])
    company_metrics = event.get('company_metrics', {})

    if not date:
        raise ValueError("Missing required field: date")

    # Even without anomalies/trends, we can still generate recommendations based on company metrics
    if not company_metrics:
        logger.warning("No company metrics provided for recommendations", extra={"date": date})
        return {
            'date': date,
            'recommendations': [],
            'message': 'Insufficient data for recommendations'
        }

    logger.info("Generating recommendations", extra={
        "date": date,
        "anomaly_count": len(anomalies),
        "trend_count": len(trends),
        "model_id": BEDROCK_MODEL_ID
    })

    # Build and send prompt to Bedrock
    prompt = build_recommendations_prompt(date, anomalies, trends, company_metrics)

    try:
        bedrock_result = invoke_bedrock(prompt)
        recommendations = parse_bedrock_response(bedrock_result['text'])

        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))

        metrics.add_metric(name="RecommendationsGenerated", unit=MetricUnit.Count, value=len(recommendations))
        metrics.add_metric(name="BedrockInvocations", unit=MetricUnit.Count, value=1)
        metrics.add_dimension(name="ModelId", value=BEDROCK_MODEL_ID)

        # Log token usage as metrics if available
        usage = bedrock_result.get('usage', {})
        if usage.get('inputTokens'):
            metrics.add_metric(name="BedrockInputTokens", unit=MetricUnit.Count, value=usage['inputTokens'])
        if usage.get('outputTokens'):
            metrics.add_metric(name="BedrockOutputTokens", unit=MetricUnit.Count, value=usage['outputTokens'])

        # Count by priority
        high_priority = sum(1 for r in recommendations if r.get('priority') == 'high')
        metrics.add_metric(name="HighPriorityRecommendations", unit=MetricUnit.Count, value=high_priority)

        logger.info("Recommendation generation complete", extra={
            "date": date,
            "recommendation_count": len(recommendations),
            "high_priority_count": high_priority,
            "input_tokens": usage.get('inputTokens'),
            "output_tokens": usage.get('outputTokens')
        })

        return {
            'date': date,
            'recommendations': recommendations,
            'recommendation_count': len(recommendations)
        }

    except Exception as e:
        logger.exception("Error invoking Bedrock for recommendations")
        metrics.add_metric(name="BedrockErrors", unit=MetricUnit.Count, value=1)
        raise
