# Serverless Smurf ETL and Analytics

A production-ready serverless ETL and analytics platform built on AWS that processes store sales data, calculates metrics, generates AI-powered insights using Amazon Bedrock, and visualizes results in Amazon QuickSight.

## Overview

This platform demonstrates an event-driven serverless architecture for **Smurf Memorabilia Inc.**, a fictional retail chain with multiple store locations. The system:

- Accepts daily JSON sales data uploads from store locations
- Validates schema and converts JSON to Parquet format (11x compression)
- Calculates per-store and company-wide metrics
- Stores aggregated data in DynamoDB using single-table design
- Triggers AI-powered analysis using Amazon Bedrock when all stores report
- Detects anomalies, analyzes trends, and generates business recommendations
- Exports data to S3 for Amazon QuickSight dashboards
- Sends daily reports and alerts via SNS

## Architecture

```
                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                     PHASE 1: Upload ETL                     │
┌──────────────┐     ┌─────────┐    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│    React     │────▶│   API   │────│─▶│  Process    │──▶│  Calculate  │──▶│   Write     │       │
│   Frontend   │     │ Gateway │    │  │  Upload     │   │   Metrics   │   │   Metrics   │       │
└──────────────┘     └─────────┘    │  │  (JSON→     │   │             │   │ (DynamoDB)  │       │
       │                            │  │   Parquet)  │   └─────────────┘   └──────┬──────┘       │
       │              ┌─────────┐   │  └─────────────┘                            │              │
       └─────────────▶│   S3    │───│───────────────────────────────────┐         │              │
         Presigned    │ Bucket  │   │                                   │         ▼              │
         URL Upload   └─────────┘   │                             ┌─────┴─────────────┐          │
                           │        │                             │  Check All Stores │          │
                           │        │                             │  (configurable)   │          │
                           ▼        │                             └─────────┬─────────┘          │
                     ┌─────────┐    └────────────────────────────────────────┼────────────────────┘
                     │  Event  │                                             │
                     │ Bridge  │                          ┌──────────────────┴─── All stores done?
                     └────┬────┘                          │                              │
                          │                               ▼                              ▼
                          │        ┌─────────────────────────────────────────────────────────────┐
                          └───────▶│                    PHASE 2: Daily Analysis                   │
                                   │                                                              │
                                   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │
                                   │  │ Get Store   │──▶│ Calc Company│──▶│ Calc Product    │    │
                                   │  │ Summaries   │   │ Metrics     │   │ Metrics         │    │
                                   │  └─────────────┘   └─────────────┘   └────────┬────────┘    │
                                   │                                               │             │
                                   │         ┌─────────────────────────────────────┤             │
                                   │         │                                     │             │
                                   │         ▼                                     ▼             │
                                   │  ┌─────────────┐                       ┌─────────────┐      │
                                   │  │   Detect    │─────┐     ┌───────────│  Analyze    │      │
                                   │  │  Anomalies  │     │     │           │   Trends    │      │
                                   │  │  (Bedrock)  │     │     │           │  (Bedrock)  │      │
                                   │  └─────────────┘     │     │           └─────────────┘      │
                                   │                      ▼     ▼                                │
                                   │               ┌─────────────────┐                           │
                                   │               │    Generate     │                           │
                                   │               │ Recommendations │                           │
                                   │               │   (Bedrock)     │                           │
                                   │               └────────┬────────┘                           │
                                   │                        │                                    │
                                   │         ┌──────────────┼──────────────┐                     │
                                   │         ▼              ▼              ▼                     │
                                   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
                                   │  │  Combine    │ │  Generate   │ │  Export to  │            │
                                   │  │  Insights   │ │   Report    │ │  QuickSight │            │
                                   │  │ (DynamoDB)  │ │   (SNS)     │ │   (S3)      │            │
                                   │  └─────────────┘ └─────────────┘ └─────────────┘            │
                                   └─────────────────────────────────────────────────────────────┘
                                                                              │
                    ┌─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    PHASE 3 & 4: Analytics                                       │
│                                                                                                 │
│  ┌──────────────────────────────┐        ┌──────────────────────────────────────────────────┐  │
│  │        API Gateway           │        │              Amazon QuickSight                   │  │
│  │                              │        │                                                  │  │
│  │  GET /analytics              │        │  ┌────────────┐ ┌────────────┐ ┌────────────┐   │  │
│  │  GET /trends                 │        │  │  Overview  │ │   Trends   │ │   Store    │   │  │
│  │  GET /files                  │        │  │ Dashboard  │ │ Dashboard  │ │ Comparison │   │  │
│  │  GET /download-url           │        │  └────────────┘ └────────────┘ └────────────┘   │  │
│  └───────────────┬──────────────┘        │                                                  │  │
│                  │                        │        ▲ SPICE Import from S3                   │  │
│                  ▼                        └────────┼─────────────────────────────────────────┘  │
│  ┌───────────────────────────────┐                 │                                            │
│  │         Lambda Functions      │                 │                                            │
│  │                               │                 │                                            │
│  │  get_analytics  get_trends   │         ┌───────┴───────┐                                    │
│  │  list_files     download_url │         │  S3: quicksight/                                   │
│  └───────────────────────────────┘         │  - store_summaries.json                           │
│                  │                         │  - top_products.json                              │
│                  ▼                         │  - anomalies.json                                 │
│  ┌───────────────────────────────┐         │  - trends.json                                    │
│  │         DynamoDB              │         │  - recommendations.json                           │
│  │         SalesData             │         └───────────────┘                                   │
│  └───────────────────────────────┘                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
.
├── README.md                       # This file
├── docs/
│   ├── ARCHITECTURE.md             # Detailed architecture documentation
│   ├── DEPLOYMENT.md               # Terraform deployment guide
│   └── DIAGRAMS.md                 # Architecture diagrams
├── frontend/                       # React dashboard application
│   ├── src/
│   │   ├── App.js                  # Main application with tabs
│   │   └── ...
│   └── package.json
├── backend/                        # Backend components
│   ├── functions/                  # 17 Lambda functions
│   │   ├── generate-upload-url/    # Presigned URL generation
│   │   ├── process-upload/         # JSON→Parquet conversion & validation
│   │   ├── calculate-metrics/      # Per-store metrics calculation
│   │   ├── write-metrics/          # DynamoDB write
│   │   ├── check-all-stores/       # Check if all expected stores reported
│   │   ├── get-store-summaries/    # Query store data for analysis
│   │   ├── calc-company-metrics/   # Company-wide aggregation
│   │   ├── calc-product-metrics/   # Product performance metrics
│   │   ├── detect-anomalies/       # Bedrock anomaly detection
│   │   ├── analyze-trends/         # Bedrock trend analysis
│   │   ├── generate-recommendations/# Bedrock business recommendations
│   │   ├── combine-insights/       # Aggregate AI insights to DynamoDB
│   │   ├── generate-report/        # Format daily report for SNS
│   │   ├── export-to-quicksight/   # Export data to S3 for QuickSight
│   │   ├── list-files/             # List processed files
│   │   ├── generate-download-url/  # Download presigned URLs
│   │   ├── get-analytics/          # API: Get analytics data
│   │   └── get-trends/             # API: Get trend data
│   ├── state-machines/             # Step Functions definitions
│   │   ├── upload-processor.json   # Upload ETL workflow
│   │   └── daily-analysis.json     # Daily analysis workflow
│   └── build-all.sh                # Build all Lambda functions
├── infrastructure/                 # Terraform configuration
│   ├── main.tf                     # Provider configuration
│   ├── variables.tf                # Input variables
│   ├── outputs.tf                  # Output values
│   ├── iam.tf                      # IAM roles and policies
│   ├── lambda.tf                   # 17 Lambda function definitions
│   ├── api-gateway.tf              # REST API configuration
│   ├── s3.tf                       # S3 bucket and CORS
│   ├── dynamodb.tf                 # DynamoDB table (single-table design)
│   ├── sns.tf                      # SNS topics for alerts/reports
│   ├── eventbridge.tf              # EventBridge rules
│   ├── step-functions.tf           # Step Functions state machines
│   └── cloudwatch.tf               # CloudWatch log groups
├── scripts/                        # Utility scripts
│   ├── generate_sample_data.py     # Generate sample store data
│   └── upload_sample_data.sh       # Upload sample data with throttling
└── sample_data/                    # Generated sample data (330 files)
```

## AWS Services Used

| Service | Purpose |
|---------|---------|
| **Lambda** | 17 serverless functions for all processing |
| **API Gateway** | REST API for frontend (upload, download, analytics) |
| **S3** | Object storage for uploads, Parquet files, QuickSight exports |
| **DynamoDB** | Single-table design for metrics, insights, and tracking |
| **Step Functions** | Two workflows: upload-processor, daily-analysis |
| **EventBridge** | S3 event routing to trigger upload workflow |
| **Amazon Bedrock** | Nova Lite for anomaly detection, trends, recommendations |
| **Amazon QuickSight** | Business intelligence dashboards (SPICE) |
| **SNS** | Email/SMS alerts and daily reports |
| **CloudWatch** | Logging, metrics, and X-Ray tracing |
| **IAM** | Least-privilege security policies |

## Data Flow

### Phase 1: Upload ETL (Per-File)
1. **Frontend** requests presigned URL via API Gateway
2. **S3** receives direct upload of store sales JSON
3. **EventBridge** triggers Step Functions on S3 ObjectCreated
4. **Process Upload** validates schema, converts to Parquet (11x compression)
5. **Calculate Metrics** computes store totals, top products, payment breakdown
6. **Write Metrics** stores aggregated data in DynamoDB
7. **Check All Stores** verifies if all expected stores reported for the day

### Phase 2: Daily Analysis (When All Stores Complete or Scheduled)
Triggered automatically when all expected stores complete uploads, or by a scheduled EventBridge rule (default: 11 PM local time) as a fallback for days when some stores fail to report.

1. **Get Store Summaries** retrieves all store data for the date
2. **Calc Company Metrics** aggregates across all stores
3. **Calc Product Metrics** identifies top/bottom performers
4. **Bedrock Analysis** (parallel):
   - Detect Anomalies (unusual patterns)
   - Analyze Trends (week-over-week, patterns)
5. **Generate Recommendations** creates actionable business advice
6. **Combine Insights** stores AI results in DynamoDB
7. **Generate Report** formats summary for SNS distribution
8. **Export to QuickSight** writes NDJSON to S3 for SPICE import

### Phase 3: Data Access APIs
- `GET /analytics` - Latest company metrics and insights
- `GET /trends` - Historical trend data by store
- `GET /files` - List processed Parquet files
- `GET /download-url` - Generate presigned download URL

### Phase 4: QuickSight Dashboards
- **Overview Dashboard** - Company KPIs, store performance
- **Trends Dashboard** - 30-day historical analysis
- **Store Comparison** - Individual store metrics
- Data refreshed via SPICE import from S3 exports

## Prerequisites

- **AWS Account** with appropriate permissions
- **AWS CLI** configured with credentials
- **Terraform** >= 1.0
- **Python** 3.12+ (for Lambda development)
- **Node.js** >= 18 (for frontend)

### AWS Permissions Required
- Lambda, API Gateway, S3, DynamoDB, Step Functions
- EventBridge, SNS, CloudWatch, IAM
- Amazon Bedrock (Nova Lite model access)
- Amazon QuickSight (optional, for dashboards)

## Quick Start

### 1. Build Lambda Functions

```bash
cd backend
./build-all.sh
```

### 2. Deploy Infrastructure

```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

Note the outputs:
- `api_endpoint` - API Gateway URL for frontend
- `upload_bucket` - S3 bucket name

### 3. Configure Frontend

```bash
cd frontend
npm install

# Configure API URL from Terraform output
./configure-api.sh

npm start
```

### 4. Generate and Upload Sample Data

```bash
# Generate 30 days of sample data (330 files)
cd scripts
python3 generate_sample_data.py

# Upload with rate limiting (30s between days)
./upload_sample_data.sh --days 30 --delay 30
```

### 5. Monitor Processing

```bash
# Watch Step Functions executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:upload-processor

# View Lambda logs
aws logs tail /aws/lambda/process_upload --follow
```

## Configuration

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region |
| `upload_prefix` | `uploads/` | S3 prefix for uploads |
| `processed_prefix` | `processed/` | S3 prefix for Parquet files |
| `expected_stores` | `11` | Number of expected stores |
| `alert_email` | `""` | Email for SNS notifications |
| `bedrock_model_id` | `amazon.nova-lite-v1:0` | Bedrock model |
| `daily_analysis_schedule` | `cron(0 23 * * ? *)` | Scheduled analysis time (UTC) |
| `daily_analysis_timezone` | `America/New_York` | Timezone for "today" |
| `enable_scheduled_analysis` | `true` | Enable scheduled fallback |

### DynamoDB Schema (Single-Table Design)

| Entity | PK | SK | GSI1PK | GSI1SK |
|--------|----|----|--------|--------|
| Store Summary | `STORE#0001` | `DATE#2025-11-27` | `DATE#2025-11-27` | `STORE#0001` |
| Company Metrics | `COMPANY` | `DATE#2025-11-27` | `DATE#2025-11-27` | `COMPANY` |
| Product Metrics | `PRODUCTS` | `DATE#2025-11-27` | - | - |
| Insights | `INSIGHTS` | `DATE#2025-11-27` | - | - |

## Sample Data

The sample data generator creates realistic transaction data:

- **Multiple stores** with different performance tiers (flagship, mall, rural, etc.)
- **30 days** of data (Oct 29 - Nov 27, 2025)
- **~200 transactions per store per day** with variation
- **20 products** (figurines, plush toys, t-shirts, mugs, etc.)
- **Weekend seasonality** (Fri/Sat/Sun higher sales)
- **Product popularity waves** across stores

Total: ~66,000 transactions, ~115,000 line items

## Compression Results

JSON to Parquet conversion achieves **~11x compression**:
- JSON uploads: 53.1 MB
- Parquet processed: 4.7 MB

## Step Function Retry Logic

Both workflows include retry with exponential backoff:

```json
{
  "ErrorEquals": ["Lambda.TooManyRequestsException", "Lambda.ServiceException"],
  "IntervalSeconds": 5,
  "MaxAttempts": 6,
  "BackoffRate": 2,
  "JitterStrategy": "FULL"
}
```

## Monitoring

### CloudWatch Logs
```bash
aws logs tail /aws/lambda/process_upload --follow
aws logs tail /aws/lambda/detect_anomalies --follow
```

### Step Functions Console
View execution history, input/output, and failures

### QuickSight Dashboards
Refresh SPICE datasets after daily analysis completes:
```bash
aws quicksight create-ingestion \
  --aws-account-id ACCOUNT_ID \
  --data-set-id sales-store-summaries-dataset \
  --ingestion-id "refresh-$(date +%Y%m%d%H%M%S)"
```

## Troubleshooting

### Upload Processing Fails
- Check Lambda logs for schema validation errors
- Verify JSON matches expected sales data format
- Check Step Functions execution history for detailed error

### Daily Analysis Not Triggering
- Verify all expected stores uploaded for the date
- Check DynamoDB for store records with correct date
- If using scheduled fallback, check the trigger_daily_analysis Lambda logs
- Verify `enable_scheduled_analysis` is true in your tfvars
- Check that the timezone is correctly configured for your region
- Manually trigger: `aws stepfunctions start-execution --state-machine-arn ARN --input '{"date":"2025-11-27"}'`

### Bedrock Errors
- Verify Bedrock model access is enabled in your region
- Check IAM role has `bedrock:InvokeModel` permission
- Review Lambda logs for throttling or quota errors

### QuickSight Missing Data
- Verify S3 exports exist: `aws s3 ls s3://bucket/quicksight/`
- Trigger SPICE refresh for all datasets
- Check manifest.json files point to correct S3 paths

## Cost Estimate

For a typical month (e.g., 330 files = multiple stores × 30 days):

| Service | Monthly Cost |
|---------|-------------|
| Lambda (17 functions) | ~$2.00 |
| Step Functions (2 workflows) | ~$0.50 |
| DynamoDB (on-demand) | ~$1.00 |
| S3 Storage (~60 MB) | ~$0.01 |
| Bedrock (Nova Lite) | ~$5.00 |
| EventBridge | Free tier |
| SNS | ~$0.10 |
| CloudWatch Alarms (7) | Free tier |
| **Total** | **~$8.61/month** |

Optional QuickSight adds ~$24/month for author access.

## Security

- **Presigned URLs**: Time-limited (1 hour), scoped to specific key
- **IAM Roles**: Least-privilege policies per Lambda function
- **CORS**: Restricts browser access to specified origins
- **No credentials in code**: All access via IAM roles
- **Schema validation**: Rejects malformed uploads

## Cleanup
Run the following terraform command to destroy all the infrastructure.

terraform destroy (from the infrastructure directory)

## Read More
This repository is associated with the following blog https://darryl-ruggles.cloud/building-a-serverless-sales-analytics-platform-with-ai-insights-for-under-10month

## License

MIT License

## Author

Darryl Ruggles

---
**Last Updated:** 2025-11-28
