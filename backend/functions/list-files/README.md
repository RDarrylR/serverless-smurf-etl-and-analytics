# List Files Lambda Function

## Purpose

API endpoint that lists processed and rejected files from S3. Returns file metadata including Hive partition information for processed files and error details for rejected files.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 30 seconds
- **Memory:** 1024 MB
- **Environment Variables:**
  - `S3_BUCKET`: S3 bucket name
  - `PROCESSED_PREFIX`: Prefix for processed files (e.g., "processed/")
  - `REJECTED_PREFIX`: Prefix for rejected files (e.g., "rejected/")
  - `FRONTEND_ORIGIN`: Allowed CORS origin (default: "*")

## Input

API Gateway event with GET request:

```
GET /files?status=all
```

Query Parameters:
- `status` (optional): Filter by status - `all`, `processed`, or `rejected` (default: `all`)

## Output

```json
{
  "statusCode": 200,
  "body": {
    "files": [
      {
        "key": "processed/year=2025/month=01/day=15/store_id=0001/data.parquet",
        "name": "store_0001_2025-01-15.parquet",
        "size": 12345,
        "last_modified": "2025-01-15T14:30:22Z",
        "status": "processed",
        "partitions": {
          "year": "2025",
          "month": "01",
          "day": "15",
          "store_id": "0001"
        }
      },
      {
        "key": "rejected/invalid_data.json",
        "name": "invalid_data.json",
        "size": 1234,
        "last_modified": "2025-01-15T14:30:22Z",
        "status": "rejected",
        "error": "Schema validation failed: missing required field 'store_id'"
      }
    ],
    "count": 2
  }
}
```

## Features

- Lists files from both processed and rejected prefixes
- Parses Hive-style partition paths for processed files
- Generates user-friendly display names
- Fetches error details from `.error.json` sidecar files
- Supports status filtering
- Sorts by last modified (newest first)
- CORS enabled for browser access

## Hive Partition Parsing

Processed files use Hive-style partitioning:
```
processed/year=2025/month=01/day=15/store_id=0001/data.parquet
```

The function extracts partition values and returns them in the `partitions` field.

## Error Details

For rejected files, the function looks for a corresponding `.error.json` file containing error details:
```
rejected/invalid_data.json        <- main file
rejected/invalid_data.error.json  <- error details
```

## IAM Permissions Required

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:ListBucket"
  ],
  "Resource": "arn:aws:s3:::BUCKET_NAME"
}
```

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject"
  ],
  "Resource": [
    "arn:aws:s3:::BUCKET_NAME/processed/*",
    "arn:aws:s3:::BUCKET_NAME/rejected/*"
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

This creates `list-files.zip` in the functions directory.
