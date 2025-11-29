# Analyze Trends Lambda Function

## Purpose

Uses Amazon Bedrock (Nova Lite) to analyze sales trends by comparing current day's metrics against the previous 7 days of historical data.

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
  - `DYNAMODB_TABLE`: DynamoDB table name (default: "SalesData")

## Input

```json
{
  "date": "2025-01-15",
  "store_summaries": [
    {
      "store_id": "0001",
      "total_sales": 1234.56,
      "transaction_count": 45,
      "top_products": [...]
    }
  ],
  "company_metrics": {
    "total_sales": 12345.67,
    "total_transactions": 450,
    "store_count": 11
  }
}
```

## Output

```json
{
  "date": "2025-01-15",
  "trends": [
    {
      "type": "growth|decline|shift|emerging|anomaly",
      "title": "Brief description",
      "description": "Detailed explanation",
      "metric": "sales|transactions|products",
      "change_percent": 15.5,
      "time_period": "week"
    }
  ],
  "trend_count": 3,
  "historical_days_used": 7,
  "stores_with_history": 8
}
```

## Features

- Queries 7 days of historical data from DynamoDB
- Compares daily and weekly trends across stores
- Uses Amazon Bedrock for AI-powered trend analysis
- Tracks token usage and estimated costs
- Handles stores with varying amounts of historical data

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

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:Query"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/SalesData",
    "arn:aws:dynamodb:*:*:table/SalesData/index/GSI1"
  ]
}
```

## Dependencies

- `boto3` (included in Lambda runtime)
- `aws-lambda-powertools` (via Lambda Layer)

## Building

```bash
./build.sh
```

This creates `analyze-trends.zip` in the functions directory.

## Bedrock Cost Tracking

The function logs estimated costs for each Bedrock invocation based on token usage:
- Input tokens: $0.00006 per 1,000 tokens (Nova Lite)
- Output tokens: $0.00024 per 1,000 tokens (Nova Lite)
