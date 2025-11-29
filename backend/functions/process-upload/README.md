# Process Upload Lambda Function

## Purpose

Processes JSON files uploaded to S3 by converting them to Apache Parquet format for optimized analytics and storage.

## Handler

`process_upload.lambda_handler`

## Runtime

- **Python:** 3.13
- **Architecture:** arm64 (Graviton2)

## Configuration

- **Timeout:** 30 seconds
- **Memory:** 1024 MB
- **Lambda Layer:** AWSSDKPandas-Python313-arm64 (for pandas and awswrangler)
- **Environment Variables:**
  - `S3_BUCKET`: S3 bucket name (e.g., "<your-bucket-name>")

## Input

EventBridge event from S3 via Step Functions:

```json
{
  "detail": {
    "bucket": {
      "name": "<your-bucket-name>"
    },
    "object": {
      "key": "uploads/20250122_143022_data.json"
    }
  }
}
```

## Output

```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Successfully processed upload\", \"key\": \"uploads/20250122_143022_data.json\"}"
}
```

## ETL Process

1. **Extract:** Download JSON file from S3 to `/tmp/input.json`
2. **Transform:** Read JSON into Pandas DataFrame
3. **Load:** Convert DataFrame to Parquet and upload to S3

## Features

- Automatic JSON to Parquet conversion
- Preserves original JSON file
- Creates Parquet file with same name (different extension)
- Uses AWS Data Wrangler for efficient S3 operations
- Columnar storage reduces file size by ~40-60%

## IAM Permissions Required

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::BUCKET_NAME/uploads/*"
}
```

## Dependencies

**Via Lambda Layer (AWSSDKPandas-Python313-arm64):**
- `awswrangler` - AWS Data Wrangler for S3/Parquet operations
- `pandas` - Data manipulation and DataFrame operations
- `boto3` - AWS SDK for Python

## Building

```bash
./build.sh
```

This creates `process-upload.zip` in the functions directory.

**Note:** Dependencies are provided by the AWS Lambda Layer, so they don't need to be included in the deployment package.

## Testing Locally

```python
import json
from process_upload import lambda_handler

event = {
    'detail': {
        'bucket': {'name': 'test-bucket'},
        'object': {'key': 'uploads/test.json'}
    }
}

response = lambda_handler(event, None)
print(json.dumps(response, indent=2))
```

## Parquet Benefits

- **Compression:** 40-60% smaller than JSON
- **Query Performance:** Columnar format enables predicate pushdown
- **Schema Evolution:** Embedded schema in file
- **Analytics Ready:** Native support in Athena, Glue, Spark

## Error Handling

- Comprehensive error logging with traceback
- Returns 500 status code on failure
- Step Functions retry logic handles transient failures (3 attempts)

## Troubleshooting

**File too large:**
- Increase Lambda timeout (current: 30s)
- Increase memory allocation (more memory = faster processing)

**Out of memory:**
- Process file in chunks if very large
- Increase Lambda memory (current: 1024 MB)

**JSON parse errors:**
- Validate JSON format before upload
- Check for malformed JSON in CloudWatch logs
