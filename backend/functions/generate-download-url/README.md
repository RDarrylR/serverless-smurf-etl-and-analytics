# Generate Download URL Lambda Function

## Purpose

Generates presigned S3 URLs that allow the frontend to securely download processed Parquet files directly from S3.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 10 seconds
- **Memory:** 1024 MB
- **Environment Variables:**
  - `S3_BUCKET`: S3 bucket name
  - `FRONTEND_ORIGIN`: Allowed CORS origin (default: "*")

## Input

API Gateway event with POST request:

```json
{
  "body": "{\"key\": \"processed/year=2025/month=01/day=15/store_id=0001/data.parquet\"}"
}
```

## Output

```json
{
  "statusCode": 200,
  "headers": {
    "Access-Control-Allow-Origin": "*"
  },
  "body": "{\"downloadUrl\": \"https://...\", \"key\": \"processed/...\"}"
}
```

## Features

- Generates presigned URLs valid for 1 hour
- Validates that the requested key is within allowed prefixes
- Handles CORS preflight (OPTIONS) requests
- Supports both processed and rejected file downloads

## Allowed Download Prefixes

The function only generates download URLs for files under these prefixes:
- `processed/` - Successfully processed Parquet files
- `rejected/` - Files that failed validation

## IAM Permissions Required

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

This creates `generate-download-url.zip` in the functions directory.

## Security

- Validates file key prefix before generating URL
- Returns 400 error for unauthorized paths
- URLs expire after 1 hour
- CORS headers restrict browser access
