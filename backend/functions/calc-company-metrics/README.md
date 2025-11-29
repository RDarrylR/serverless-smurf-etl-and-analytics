# Calculate Company Metrics Lambda Function

## Purpose

Aggregates store-level metrics into company-wide totals. Calculates KPIs including total sales, transactions, payment breakdowns, and identifies best/worst performing stores.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 30 seconds
- **Memory:** 1024 MB

## Input

```json
{
  "date": "2025-01-15",
  "store_summaries": [
    {
      "store_id": "0001",
      "total_sales": 1234.56,
      "transaction_count": 45,
      "item_count": 120,
      "payment_breakdown": {
        "cash": 500.00,
        "credit": 600.00,
        "debit": 134.56
      }
    }
  ],
  "store_count": 11
}
```

## Output

```json
{
  "date": "2025-01-15",
  "company_metrics": {
    "total_sales": 12345.67,
    "total_transactions": 450,
    "total_items": 1320,
    "avg_transaction": 27.43,
    "store_count": 11,
    "best_store": {
      "store_id": "0003",
      "total_sales": 2500.00
    },
    "worst_store": {
      "store_id": "0007",
      "total_sales": 800.00
    },
    "payment_breakdown": {
      "cash": 3500.00,
      "credit": 6000.00,
      "debit": 2000.00,
      "gift_card": 845.67
    }
  }
}
```

## Features

- Aggregates sales across all stores
- Calculates average transaction value
- Identifies best and worst performing stores
- Aggregates payment method breakdowns
- Returns zero values if no store data available

## Metrics Calculated

| Metric | Description |
|--------|-------------|
| `total_sales` | Sum of sales across all stores |
| `total_transactions` | Sum of transactions across all stores |
| `total_items` | Sum of items sold across all stores |
| `avg_transaction` | Average transaction value (total_sales / total_transactions) |
| `store_count` | Number of stores reporting |
| `best_store` | Store with highest sales |
| `worst_store` | Store with lowest sales |
| `payment_breakdown` | Sum by payment method (cash, credit, debit, gift_card) |

## Dependencies

- `boto3` (included in Lambda runtime)
- `aws-lambda-powertools` (via Lambda Layer)

## Building

```bash
./build.sh
```

This creates `calc-company-metrics.zip` in the functions directory.
