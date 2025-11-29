# Get Analytics Lambda Function

## Purpose

API endpoint that fetches analytics data from DynamoDB for the frontend dashboard. Returns store summaries, top products, and AI insights for a requested date.

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

API Gateway event with GET request:

```
GET /analytics?date=2025-01-15
```

Query Parameters:
- `date` (optional): Specific date to fetch. Defaults to most recent available date.

## Output

```json
{
  "statusCode": 200,
  "body": {
    "date": "2025-01-15",
    "available_dates": ["2025-01-15", "2025-01-14", "2025-01-13"],
    "kpis": {
      "total_sales": 12345.67,
      "total_transactions": 450,
      "total_items": 1320,
      "avg_transaction": 27.43,
      "store_count": 11,
      "payment_breakdown": {...}
    },
    "stores": [
      {
        "store_id": "0001",
        "total_sales": 1234.56,
        "transaction_count": 45,
        "item_count": 120,
        "avg_transaction": 27.43,
        "payment_breakdown": {...}
      }
    ],
    "top_products": [
      {
        "sku": "SMF-001",
        "name": "Papa Smurf Figurine",
        "units_sold": 150,
        "revenue": 2998.50
      }
    ],
    "anomalies": [...],
    "trends": [...],
    "recommendations": [...]
  }
}
```

## Features

- Returns available dates for date picker
- Aggregates KPIs from store summaries
- Extracts and ranks top products across stores
- Includes AI-generated insights (anomalies, trends, recommendations)
- CORS enabled for browser access
- Handles OPTIONS preflight requests

## DynamoDB Access Patterns

1. **Get available dates**: Scan GSI1PK for unique `DATE#` prefixes
2. **Get store summaries**: Query GSI1 with `GSI1PK = DATE#yyyy-mm-dd`
3. **Get insights**: Query main table with `PK = DATE#yyyy-mm-dd` and `SK begins_with INSIGHT#`

## IAM Permissions Required

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:Query",
    "dynamodb:Scan"
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

This creates `get-analytics.zip` in the functions directory.

## Error Handling

- Returns empty data structure if no data available
- Falls back to most recent date if requested date not found
- Returns 200 with empty arrays rather than 404 for missing data
