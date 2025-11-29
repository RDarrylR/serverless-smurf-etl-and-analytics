# Generate Upload URL Lambda Function

## Purpose

Generates presigned S3 URLs that allow the frontend to securely upload files directly to S3 without passing through API Gateway or Lambda.

## Handler

`lambda_function.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 10 seconds
- **Memory:** 1024 MB
- **Environment Variables:**
  - `S3_BUCKET`: S3 bucket name (e.g., "<your-bucket-name>")
  - `UPLOAD_PREFIX`: Prefix for uploaded files (e.g., "uploads/")

## Input

API Gateway event with POST request:

```json
{
  "body": "{\"filename\": \"data.json\"}"
}
```

## Output

```json
{
  "statusCode": 200,
  "headers": {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Credentials": "true"
  },
  "body": "{\"uploadUrl\": \"https://...\", \"key\": \"uploads/20250122_143022_data.json\"}"
}
```

## Features

- Generates presigned URLs valid for 1 hour
- Adds timestamp to filename to prevent collisions
- Handles CORS preflight (OPTIONS) requests
- Returns both the upload URL and the S3 key

## IAM Permissions Required

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject"
  ],
  "Resource": "arn:aws:s3:::BUCKET_NAME/uploads/*"
}
```

## Building

```bash
./build.sh
```

This creates `generate-upload-url.zip` in the functions directory.

## Testing Locally

```python
import json
from lambda_function import lambda_handler

event = {
    'httpMethod': 'POST',
    'body': json.dumps({'filename': 'test.json'})
}

response = lambda_handler(event, None)
print(json.dumps(response, indent=2))
```

## Dependencies

- `boto3` (included in Lambda runtime)
- No external dependencies
