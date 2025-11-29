# Get Trends Lambda Function

## Purpose

API endpoint that fetches historical sales data for trending analytics visualization. Returns time-series data for stores and products over a configurable number of days.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 60 seconds
- **Memory:** 1024 MB
- **Environment Variables:**
  - `DYNAMODB_TABLE`: DynamoDB table name (default: "SalesData")

## Input

API Gateway event with GET request:

```
GET /trends?days=30&store_id=0001
```

Query Parameters:
- `days` (optional): Number of days of history (default: 30)
- `store_id` (optional): Filter to specific store

## Output

```json
{
  "statusCode": 200,
  "body": {
    "stores": ["0001", "0002", "0003"],
    "dates": ["2025-01-01", "2025-01-02", ...],
    "days_requested": 30,
    "available_dates": [...],
    "time_series": [
      {
        "date": "2025-01-15",
        "total_sales": 12345.67,
        "total_transactions": 450,
        "0001_sales": 1234.56,
        "0001_transactions": 45,
        "0002_sales": 1500.00,
        "0002_transactions": 50
      }
    ],
    "store_summaries": [
      {
        "store_id": "0001",
        "total_sales": 35000.00,
        "total_transactions": 1200,
        "avg_daily_sales": 1166.67,
        "days_with_data": 30,
        "trend_percent": 15.5
      }
    ],
    "product_trends": [
      {
        "sku": "SMF-001",
        "name": "Papa Smurf Figurine",
        "total_units_sold": 4500,
        "total_revenue": 89955.00,
        "avg_daily_units": 150,
        "avg_daily_revenue": 2998.50,
        "days_sold": 30,
        "trend_direction": "increasing",
        "trend_percent": 12.5,
        "daily_history": [...]
      }
    ]
  }
}
```

## Features

- Time-series data optimized for charts
- Store performance summaries with trend calculations
- Product trends with daily history
- Configurable date range
- Optional store filtering
- CORS enabled for browser access

## Trend Calculations

**Store Trends:**
- Compares first day to last day sales
- Calculates percentage change over period

**Product Trends:**
- Compares first half vs second half of period
- Classifies as: `increasing`, `decreasing`, `stable`, or `insufficient_data`
- Calculates trend percentage

## DynamoDB Access Patterns

1. **Get available dates**: Scan GSI1PK for unique `DATE#` prefixes
2. **Get store data per date**: Query GSI1 with `GSI1PK = DATE#yyyy-mm-dd`
3. **Get product data per date**: Query main table with `PK = DATE#yyyy-mm-dd`, `SK begins_with PRODUCT#`

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

This creates `get-trends.zip` in the functions directory.
