# Backend Components

This directory contains all backend components for the Serverless Sales Data Platform.

## Directory Structure

```
backend/
├── functions/                    # Lambda function implementations (17 functions)
│   ├── generate-upload-url/      # Phase 1: Presigned URL generation
│   ├── process-upload/           # Phase 1: JSON validation & Parquet conversion
│   ├── calculate-metrics/        # Phase 1: Store metrics calculation
│   ├── write-metrics/            # Phase 1: DynamoDB metrics writer
│   ├── check-all-stores/         # Phase 1: Daily completion checker
│   ├── get-store-summaries/      # Phase 2: Query store data for analysis
│   ├── calc-company-metrics/     # Phase 2: Company-wide aggregation
│   ├── calc-product-metrics/     # Phase 2: Product performance metrics
│   ├── detect-anomalies/         # Phase 2: Anomaly detection (Bedrock)
│   ├── analyze-trends/           # Phase 2: Trend analysis (Bedrock)
│   ├── generate-recommendations/ # Phase 2: AI recommendations (Bedrock)
│   ├── combine-insights/         # Phase 2: Aggregate AI insights to DynamoDB
│   ├── generate-report/          # Phase 2: Format daily report for SNS
│   ├── export-to-quicksight/     # Phase 2: Export to S3 for QuickSight
│   ├── list-files/               # Phase 3: List processed files API
│   ├── generate-download-url/    # Phase 3: Download presigned URLs API
│   ├── get-analytics/            # Phase 3: Get analytics data API
│   └── get-trends/               # Phase 3: Get trend data API
├── state-machines/               # Step Functions definitions
│   ├── upload-processor.json     # Upload processing workflow
│   └── daily-analysis.json       # Daily analysis workflow
├── quicksight/                   # QuickSight configuration and scripts
│   ├── setup-quicksight.sh       # Setup QuickSight datasets
│   └── dashboard-definition.json # Dashboard export
├── build-all.sh                  # Build all Lambda functions
└── README.md                     # This file
```

**Note:** The `trigger-daily-analysis` Lambda is defined inline in `infrastructure/eventbridge.tf` rather than as a separate function directory.

## Lambda Functions

All Lambda functions use:
- **Runtime:** Python 3.13
- **Architecture:** arm64 (Graviton2)
- **Memory:** 1024 MB

### Phase 1: Upload ETL Pipeline

| Function | Purpose | Timeout |
|----------|---------|---------|
| `generate-upload-url` | Generate presigned S3 URLs for uploads | 10s |
| `process-upload` | Validate JSON schema, convert to Parquet | 30s |
| `calculate-metrics` | Calculate store-level sales metrics | 30s |
| `write-metrics` | Write metrics to DynamoDB | 10s |
| `check-all-stores` | Check if all stores reported for a date | 10s |

### Scheduled Trigger

| Function | Purpose | Timeout |
|----------|---------|---------|
| `trigger-daily-analysis` | Scheduled fallback trigger for daily analysis | 30s |

The `trigger-daily-analysis` Lambda is invoked by an EventBridge scheduled rule (default: 11 PM local time). It checks if daily analysis already ran for the current date and starts it if not. This ensures daily reports are generated even when some stores fail to upload.

### Phase 2: Daily Analysis

| Function | Purpose | Timeout |
|----------|---------|---------|
| `get-store-summaries` | Retrieve store summaries for analysis | 30s |
| `calc-company-metrics` | Calculate company-wide metrics | 30s |
| `calc-product-metrics` | Calculate product-level metrics | 30s |
| `detect-anomalies` | Detect statistical anomalies | 60s |
| `analyze-trends` | Analyze sales trends over time | 60s |
| `generate-recommendations` | Generate AI recommendations via Bedrock | 60s |
| `combine-insights` | Combine analysis results | 30s |
| `generate-report` | Format daily analysis report | 10s |
| `export-to-quicksight` | Export NDJSON for QuickSight | 120s |

### Phase 3: Data Access APIs

| Function | Purpose | Timeout |
|----------|---------|---------|
| `list-files` | List uploaded/processed files from S3 | 10s |
| `get-analytics` | Query analytics and metrics | 30s |
| `get-trends` | Retrieve trend analysis data | 30s |
| `download-file` | Generate presigned URL for Parquet download | 10s |

## State Machines

### Upload Processor

**File:** `state-machines/upload-processor.json`

Orchestrates the file upload processing pipeline:

```
S3 Upload Event
      ↓
ProcessUpload (validate JSON, convert to Parquet)
      ↓
CheckProcessResult (success/failure)
      ↓
CalculateMetrics (compute sales metrics)
      ↓
WriteMetrics (store in DynamoDB)
      ↓
CheckAllStores (all expected stores reported?)
      ↓
[If all done] → TriggerDailyAnalysis
```

**Features:**
- Retry with exponential backoff and jitter
- Lambda throttling protection (TooManyRequestsException)
- Error handling with SNS notifications
- Automatic daily analysis trigger

### Daily Analysis

**File:** `state-machines/daily-analysis.json`

Orchestrates the daily analysis workflow:

```
Trigger (all stores reported)
      ↓
AggregateDaily (combine all store metrics)
      ↓
Parallel Processing:
├── DetectAnomalies (find outliers)
├── AnalyzeTrends (7-day patterns)
└── ExportToQuickSight (NDJSON export)
      ↓
GenerateRecommendations (Bedrock AI)
      ↓
FormatReport (create email content)
      ↓
SendReport (SNS email)
```

## Building Lambda Functions

### Build All Functions

```bash
cd backend
./build-all.sh
```

**Output:**
```
Building all Lambda functions...
Building generate-upload-url...
  ✓ Package created: functions/generate-upload-url/package/
Building process-upload...
  ✓ Package created: functions/process-upload/package/
...
✓ All 17 Lambda functions built successfully
```

### Build Individual Function

```bash
cd backend/functions/<function-name>
./build.sh
```

### Build Requirements

- Python 3.13
- pip with platform support for Linux ARM64

The build script:
1. Creates a `package/` directory
2. Installs dependencies for Linux ARM64 (Lambda runtime)
3. Copies Lambda handler and supporting files
4. Terraform then packages this for deployment

## Dependencies

### Lambda Layer: AWS SDK Pandas

Functions that process data use the AWS-provided Lambda layer:

```
arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python313-Arm64:3
```

This provides:
- pandas
- numpy
- pyarrow (Parquet support)
- awswrangler

### Common Dependencies

Most functions use only boto3 (included in Lambda runtime).

Functions with additional dependencies:
- `process-upload`: jsonschema (for JSON validation)
- `calculate-metrics`: Uses Lambda layer
- Analysis functions: Uses Lambda layer

## API Gateway

**File:** `apis/file-upload-api.yaml`

OpenAPI 3.0 specification defining:

| Endpoint | Method | Function | Description |
|----------|--------|----------|-------------|
| `/generate-upload-url` | POST | generate-upload-url | Get presigned URL |
| `/files` | GET | list-files | List uploaded files |
| `/files/{key}` | GET | download-file | Download Parquet file |
| `/metrics` | GET | get-metrics | Get store metrics |
| `/recommendations` | GET | get-recommendations | Get AI recommendations |

All endpoints include:
- CORS configuration
- Request validation
- Lambda proxy integration

## Development Workflow

### 1. Make Code Changes

```bash
cd backend/functions/<function-name>
# Edit the Lambda handler
vim lambda_function.py
```

### 2. Build the Function

```bash
./build.sh
```

### 3. Deploy via Terraform

```bash
cd ../../infrastructure
terraform apply
```

### 4. Test the Function

```bash
# Invoke directly
aws lambda invoke \
  --function-name <function-name> \
  --payload '{"key": "value"}' \
  response.json

# Check logs
aws logs tail /aws/lambda/<function-name> --follow
```

## Testing

### Local Testing

```bash
cd backend/functions/<function-name>
python lambda_function.py
```

### Integration Testing

```bash
# Upload test file
cd ../../scripts
./upload_sample_data.sh --days 1 --delay 0

# Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn <arn> \
  --max-results 5
```

### Validate State Machines

```bash
cd backend/state-machines
cat upload-processor.json | jq .
cat daily-analysis.json | jq .
```

## Monitoring

### CloudWatch Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/process_upload --follow
aws logs tail /aws/lambda/generate_recommendations --follow

# Step Functions logs
aws logs tail /aws/stepfunctions/upload-processor --follow
aws logs tail /aws/stepfunctions/daily-analysis --follow
```

### Key Metrics

| Service | Metric | Alert Threshold |
|---------|--------|-----------------|
| Lambda | Errors | > 0 |
| Lambda | Duration | > 80% of timeout |
| Lambda | Throttles | > 0 |
| Step Functions | ExecutionsFailed | > 0 |
| Step Functions | ExecutionTime | > 5 minutes |

## Adding New Functions

### 1. Create Function Directory

```bash
mkdir -p backend/functions/my-new-function
cd backend/functions/my-new-function
```

### 2. Create Lambda Handler

```python
# lambda_function.py
import json
import boto3

def lambda_handler(event, context):
    # Your logic here
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Success'})
    }
```

### 3. Create Build Script

```bash
#!/bin/bash
# build.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$SCRIPT_DIR/package"
mkdir -p "$SCRIPT_DIR/package"
cp "$SCRIPT_DIR"/*.py "$SCRIPT_DIR/package/"
echo "Package created: $SCRIPT_DIR/package/"
```

### 4. Add to Terraform

Edit `infrastructure/lambda.tf`:

```hcl
resource "aws_lambda_function" "my_new_function" {
  function_name = "my-new-function"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.13"
  architectures = ["arm64"]
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.my_new_function_zip.output_path
  source_code_hash = data.archive_file.my_new_function_zip.output_base64sha256
}
```

### 5. Update build-all.sh

Add the new function to the FUNCTIONS array:

```bash
FUNCTIONS=(
  "generate-upload-url"
  "process-upload"
  ...
  "my-new-function"
)
```

## Related Documentation

- [Project Overview](../README.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Diagrams](../docs/DIAGRAMS.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Infrastructure](../infrastructure/README.md)
