# Detect Anomalies Lambda Function

## Purpose

Uses Amazon Bedrock (Nova Lite) to analyze store sales data and identify anomalies by comparing today's metrics against the last 7 days of historical data.

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
      "transaction_count": 45
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
  "anomalies": [
    {
      "type": "historical_low",
      "severity": "warning",
      "store_id": "0007",
      "title": "Sales significantly below average",
      "description": "Store 0007 sales are 35% below the 7-day average",
      "metric_value": 800.00,
      "historical_average": 1230.00,
      "deviation_percent": -35.0
    }
  ],
  "anomaly_count": 1,
  "historical_days_used": 7,
  "stores_with_history": 8
}
```

## Features

- Queries 7 days of historical data from DynamoDB
- Calculates deviation from historical averages
- Uses Amazon Bedrock for AI-powered anomaly detection
- Categorizes anomalies by type and severity
- Skips analysis when insufficient historical data (< 3 days)

## Anomaly Types

| Type | Description |
|------|-------------|
| `historical_low` | Store performing significantly below historical average |
| `historical_high` | Store performing significantly above historical average |
| `sudden_drop` | Dramatic decrease compared to recent history |
| `sudden_spike` | Dramatic increase compared to recent history |
| `peer_outlier` | Store significantly different from peers today |

## Severity Levels

| Severity | Criteria |
|----------|----------|
| `critical` | >50% deviation from historical average |
| `warning` | 25-50% deviation from historical average |
| `info` | Notable but not concerning patterns |

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

This creates `detect-anomalies.zip` in the functions directory.

## Cold Start Handling

The function returns an empty anomalies list with a message when there's insufficient historical data (less than 3 days). This prevents false positives on first upload or when starting fresh.
