# Generate Recommendations Lambda Function

## Purpose

Uses Amazon Bedrock (Nova Lite) to generate actionable business recommendations based on detected anomalies, trends, and company metrics.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 60 seconds
- **Memory:** 1024 MB
- **Environment Variables:**
  - `BEDROCK_MODEL_ID`: Bedrock model to use (default: "amazon.nova-lite-v1:0")

## Input

```json
{
  "date": "2025-01-15",
  "anomalies": [
    {
      "type": "historical_low",
      "store_id": "0007",
      "description": "Sales 35% below average"
    }
  ],
  "trends": [
    {
      "type": "growth",
      "title": "Credit card adoption increasing"
    }
  ],
  "company_metrics": {
    "total_sales": 12345.67,
    "store_count": 11,
    "best_store": {"store_id": "0003", "total_sales": 2500.00},
    "worst_store": {"store_id": "0007", "total_sales": 800.00}
  }
}
```

## Output

```json
{
  "date": "2025-01-15",
  "recommendations": [
    {
      "priority": "high",
      "category": "operations",
      "title": "Investigate Store 0007 underperformance",
      "description": "Review staffing levels, inventory, and local competition",
      "affected_stores": ["0007"],
      "affected_products": [],
      "expected_impact": "Potential 20% sales improvement"
    }
  ],
  "recommendation_count": 4
}
```

## Features

- Generates recommendations across 4 categories
- Prioritizes by business impact (high/medium/low)
- Links recommendations to affected stores and products
- Includes expected impact descriptions
- Tracks token usage and estimated costs

## Recommendation Categories

| Category | Description |
|----------|-------------|
| `inventory` | Stock level adjustments based on product performance |
| `marketing` | Promotional opportunities based on trends |
| `operations` | Store-specific actions for underperformers |
| `strategy` | Longer-term strategic considerations |

## Priority Levels

| Priority | Description |
|----------|-------------|
| `high` | Immediate action required, significant impact |
| `medium` | Should address within 1-2 weeks |
| `low` | Nice to have, lower urgency |

## IAM Permissions Required

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel"
  ],
  "Resource": "arn:aws:bedrock:*::foundation-model/amazon.nova-lite-v1:0"
}
```

## Dependencies

- `boto3` (included in Lambda runtime)
- `aws-lambda-powertools` (via Lambda Layer)

## Building

```bash
./build.sh
```

This creates `generate-recommendations.zip` in the functions directory.

## Bedrock Cost Tracking

The function logs estimated costs for each Bedrock invocation:
- Input tokens: $0.00006 per 1,000 tokens (Nova Lite)
- Output tokens: $0.00024 per 1,000 tokens (Nova Lite)
