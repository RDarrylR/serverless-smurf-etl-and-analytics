# Calculate Metrics Lambda Function

## Purpose

Calculates sales metrics from raw transaction JSON data. Processes individual transactions to compute totals, averages, top products, and payment breakdowns for a single store.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 30 seconds
- **Memory:** 1024 MB
- **Environment Variables:**
  - `S3_BUCKET`: S3 bucket name containing transaction data

## Input

```json
{
  "detail": {
    "bucket": {
      "name": "my-bucket"
    },
    "object": {
      "key": "uploads/store_0001_2025-01-15.json"
    }
  }
}
```

## Output

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
    "payment_breakdown": {
      "cash": 500.00,
      "credit": 600.00,
      "debit": 134.56
    }
  },
  "record_count": 45,
  "source_key": "uploads/store_0001_2025-01-15.json"
}
```

## Features

- Parses store ID and date from filename
- Calculates comprehensive sales metrics
- Identifies top 10 products by revenue
- Aggregates payment method totals
- Handles various JSON input formats

## Metrics Calculated

| Metric | Description |
|--------|-------------|
| `total_sales` | Sum of all transaction totals |
| `total_discount` | Sum of all discounts applied |
| `net_sales` | total_sales - total_discount |
| `transaction_count` | Number of transactions |
| `item_count` | Total items across all transactions |
| `avg_transaction` | Average transaction value |
| `top_products` | Top 10 products by revenue |
| `payment_breakdown` | Sales by payment method |

## Filename Convention

The function extracts metadata from the S3 object key:
- Pattern: `uploads/store_XXXX_YYYY-MM-DD.json`
- Example: `uploads/store_0001_2025-01-15.json`
  - Store ID: `0001`
  - Date: `2025-01-15`

## IAM Permissions Required

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject"
  ],
  "Resource": "arn:aws:s3:::BUCKET_NAME/uploads/*"
}
```

## Dependencies

- `boto3` (included in Lambda runtime)
- `aws-lambda-powertools` (via Lambda Layer)

## Building

```bash
./build.sh
```

This creates `calculate-metrics.zip` in the functions directory.

## Error Handling

- Returns validation error if filename doesn't match expected pattern
- Handles missing or malformed transaction data gracefully
- Logs detailed errors for debugging
