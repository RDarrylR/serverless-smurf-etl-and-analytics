# Export to QuickSight Lambda Function

## Purpose

Exports daily analytics data from DynamoDB to S3 as NDJSON files for QuickSight consumption. Creates separate files for store summaries, top products, anomalies, trends, and recommendations.

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
  - `S3_BUCKET`: S3 bucket for QuickSight exports
  - `QUICKSIGHT_PREFIX`: S3 prefix for exports (default: "quicksight/")

## Input

```json
{
  "date": "2025-01-15",
  "company_metrics": {...},
  "product_metrics": [...],
  "insights": {
    "anomalies": [...],
    "trends": [...],
    "recommendations": [...]
  }
}
```

## Output

```json
{
  "date": "2025-01-15",
  "exports": {
    "store_summaries": "s3://bucket/quicksight/store_summaries/2025-01-15.json",
    "top_products": "s3://bucket/quicksight/top_products/2025-01-15.json",
    "anomalies": "s3://bucket/quicksight/anomalies/2025-01-15.json",
    "trends": "s3://bucket/quicksight/trends/2025-01-15.json",
    "recommendations": "s3://bucket/quicksight/recommendations/2025-01-15.json"
  },
  "records_exported": {
    "store_summaries": 11,
    "top_products": 20,
    "anomalies": 3,
    "trends": 5,
    "recommendations": 4
  }
}
```

## Features

- Exports data in NDJSON format (one JSON object per line)
- Creates separate datasets for different data types
- Organizes files by date for time-series analysis
- Converts DynamoDB Decimal types to JSON-compatible floats
- Supports incremental updates (append new dates)

## Exported Datasets

| Dataset | Description | S3 Path |
|---------|-------------|---------|
| `store_summaries` | Daily store performance metrics | `quicksight/store_summaries/{date}.json` |
| `top_products` | Top selling products per day | `quicksight/top_products/{date}.json` |
| `anomalies` | Detected anomalies | `quicksight/anomalies/{date}.json` |
| `trends` | Identified trends | `quicksight/trends/{date}.json` |
| `recommendations` | AI-generated recommendations | `quicksight/recommendations/{date}.json` |

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

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::BUCKET_NAME/quicksight/*"
}
```

## Dependencies

- `boto3` (included in Lambda runtime)
- `aws-lambda-powertools` (via Lambda Layer)

## Building

```bash
./build.sh
```

This creates `export-to-quicksight.zip` in the functions directory.

## QuickSight Integration

After export, QuickSight datasets can be configured to read from these S3 locations using manifest files. The NDJSON format is directly compatible with QuickSight's JSON data source.
