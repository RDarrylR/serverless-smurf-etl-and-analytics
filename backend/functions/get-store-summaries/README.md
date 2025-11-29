# Get Store Summaries Lambda Function

## Purpose

Queries all store summaries for a specific date from DynamoDB. Used by the daily analysis Step Function to retrieve store data for aggregation and AI analysis.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 30 seconds
- **Memory:** 1024 MB
- **Environment Variables:**
  - `DYNAMODB_TABLE`: DynamoDB table name (default: "SalesData")

## Input

```json
{
  "date": "2025-01-15"
}
```

## Output

```json
{
  "date": "2025-01-15",
  "store_summaries": [
    {
      "store_id": "0001",
      "date": "2025-01-15",
      "total_sales": 1234.56,
      "transaction_count": 45,
      "item_count": 120,
      "avg_transaction": 27.43,
      "top_products": [...],
      "payment_breakdown": {...}
    }
  ],
  "store_count": 11
}
```

## Features

- Queries GSI1 for efficient date-based lookup
- Returns all stores that uploaded data for the date
- Converts DynamoDB types to standard JSON
- Sorts results by store ID for consistent ordering

## DynamoDB Access Pattern

Uses GSI1 for efficient querying:
- GSI1PK: `DATE#2025-01-15`
- GSI1SK: begins with `STORE#`

This allows retrieving all store summaries for a specific date in a single query.

## IAM Permissions Required

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

This creates `get-store-summaries.zip` in the functions directory.

## Step Functions Integration

This function is the first step in the daily analysis workflow:

```
Start -> GetStoreSummaries -> CheckStoreSummaries -> [continue analysis...]
```

The output provides the raw store data that subsequent steps use for:
- Company-wide metric aggregation
- Product metric aggregation
- AI-powered anomaly detection
- AI-powered trend analysis
