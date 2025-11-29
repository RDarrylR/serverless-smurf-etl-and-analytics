# Combine Insights Lambda Function

## Purpose

Merges AI-generated insights (anomalies, trends, recommendations) from parallel Bedrock analysis into a single insights object and writes them to DynamoDB for persistence.

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

```json
{
  "date": "2025-01-15",
  "anomalies_result": {
    "anomalies": [
      {
        "type": "historical_low",
        "severity": "warning",
        "store_id": "0007",
        "title": "Sales significantly below average",
        "description": "Store 0007 sales are 35% below 7-day average"
      }
    ]
  },
  "trends_result": {
    "trends": [
      {
        "type": "growth",
        "title": "Strong credit card adoption",
        "description": "Credit card payments up 15% week-over-week"
      }
    ]
  },
  "recommendations_result": {
    "recommendations": [
      {
        "priority": "high",
        "category": "operations",
        "title": "Investigate Store 0007 performance",
        "description": "Review staffing and inventory levels"
      }
    ]
  }
}
```

## Output

```json
{
  "date": "2025-01-15",
  "insights": {
    "anomalies": [...],
    "trends": [...],
    "recommendations": [...]
  },
  "counts": {
    "anomalies": 2,
    "trends": 3,
    "recommendations": 4
  },
  "insights_written": 9
}
```

## Features

- Combines results from parallel Bedrock analysis
- Handles partial failures gracefully (continues with available data)
- Writes each insight as a separate DynamoDB item
- Assigns unique IDs to each insight for querying
- Logs any Bedrock errors encountered

## DynamoDB Schema

Each insight is stored with:
- PK: `DATE#2025-01-15`
- SK: `INSIGHT#anomaly#<uuid>` or `INSIGHT#trend#<uuid>` or `INSIGHT#recommendation#<uuid>`
- Additional attributes from the insight object

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

This creates `combine-insights.zip` in the functions directory.

## Error Handling

- If anomaly detection failed, continues with trends and recommendations
- If trend analysis failed, continues with anomalies and recommendations
- Logs warnings for any missing or error results
- Returns partial results rather than failing completely
