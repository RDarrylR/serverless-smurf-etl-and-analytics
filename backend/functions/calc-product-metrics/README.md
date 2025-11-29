# Calculate Product Metrics Lambda Function

## Purpose

Aggregates product-level metrics across all stores to identify top-selling products company-wide. Combines product data from each store's top products list.

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
      "top_products": [
        {
          "sku": "SMF-001",
          "name": "Papa Smurf Figurine",
          "units": 25,
          "revenue": 499.75
        }
      ]
    }
  ]
}
```

## Output

```json
{
  "date": "2025-01-15",
  "product_metrics": [
    {
      "sku": "SMF-001",
      "name": "Papa Smurf Figurine",
      "units_sold": 150,
      "revenue": 2998.50
    }
  ],
  "product_count": 25
}
```

## Features

- Aggregates product sales across all stores
- Combines units sold and revenue by SKU
- Returns top 20 products sorted by revenue
- Handles missing or incomplete product data

## Aggregation Logic

1. Iterates through each store's `top_products` array
2. Groups products by SKU
3. Sums `units` and `revenue` for each SKU
4. Sorts by total revenue (descending)
5. Returns top 20 products

## Dependencies

- `boto3` (included in Lambda runtime)
- `aws-lambda-powertools` (via Lambda Layer)

## Building

```bash
./build.sh
```

This creates `calc-product-metrics.zip` in the functions directory.
