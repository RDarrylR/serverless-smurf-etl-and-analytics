# Check All Stores Lambda Function

## Purpose

Checks if all expected stores have uploaded their daily data by querying DynamoDB. Used as a gate in the Step Functions workflow to determine if daily analysis should proceed.

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
  - `EXPECTED_STORES`: Comma-separated list of expected store IDs (default: "0001,0002,...,0011")

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
  "all_uploaded": true,
  "uploaded_stores": ["0001", "0002", "0003"],
  "missing_stores": [],
  "uploaded_count": 11,
  "expected_count": 11
}
```

## Features

- Queries DynamoDB GSI1 to find uploaded stores for a given date
- Compares against expected store list
- Returns detailed status including missing stores
- Supports configurable expected store list

## DynamoDB Access Pattern

Uses GSI1 to query all uploads for a specific date:
- GSI1PK: `DATE#2025-01-15`
- GSI1SK: begins with `UPLOAD#STORE#`

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

This creates `check-all-stores.zip` in the functions directory.

## Step Functions Integration

This function is typically used with a Choice state to decide whether to proceed with daily analysis:

```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.all_uploaded",
      "BooleanEquals": true,
      "Next": "RunDailyAnalysis"
    }
  ],
  "Default": "WaitForMoreUploads"
}
```
