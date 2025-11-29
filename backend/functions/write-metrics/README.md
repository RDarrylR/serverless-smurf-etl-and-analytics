# Write Metrics Lambda Function

## Purpose

Writes calculated store metrics to DynamoDB. Creates both a store summary record and an upload tracking record for each processed file.

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
  "store_id": "0001",
  "date": "2025-01-15",
  "year": "2025",
  "month": "01",
  "day": "15",
  "metrics": {
    "total_sales": 1234.56,
    "total_discount": 50.00,
    "net_sales": 1184.56,
    "transaction_count": 45,
    "item_count": 120,
    "avg_transaction": 27.43,
    "top_products": [...],
    "payment_breakdown": {...}
  },
  "record_count": 45,
  "source_key": "uploads/store_0001_2025-01-15.json"
}
```

## Output

```json
{
  "store_id": "0001",
  "date": "2025-01-15",
  "written": true,
  "items_written": 2
}
```

## DynamoDB Records Created

### 1. Store Daily Summary

Primary record for store performance on a given date.

| Attribute | Value |
|-----------|-------|
| PK | `STORE#0001` |
| SK | `DATE#2025-01-15` |
| GSI1PK | `DATE#2025-01-15` |
| GSI1SK | `STORE#0001` |
| store_id | `0001` |
| date | `2025-01-15` |
| total_sales | `1234.56` |
| transaction_count | `45` |
| ... | (all metrics) |

### 2. Upload Tracking Record

Tracks which stores have uploaded for each date.

| Attribute | Value |
|-----------|-------|
| PK | `DATE#2025-01-15` |
| SK | `UPLOAD#STORE#0001` |
| store_id | `0001` |
| date | `2025-01-15` |
| uploaded_at | `2025-01-15T14:30:22Z` |
| s3_key | `uploads/store_0001_2025-01-15.json` |
| status | `processed` |

## Features

- Creates two DynamoDB records per upload
- Supports GSI1 for efficient date-based queries
- Converts float values to Decimal for DynamoDB
- Tracks timestamps for auditing
- Idempotent (overwrites existing records)

## IAM Permissions Required

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:PutItem"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/SalesData"
}
```

## Dependencies

- `boto3` (included in Lambda runtime)
- `aws-lambda-powertools` (via Lambda Layer)

## Building

```bash
./build.sh
```

This creates `write-metrics.zip` in the functions directory.

## Data Type Conversion

The function automatically converts Python floats to DynamoDB Decimal type to avoid floating-point precision issues:

```python
# Input (float)
{"total_sales": 1234.56}

# Stored (Decimal)
{"total_sales": Decimal("1234.56")}
```
