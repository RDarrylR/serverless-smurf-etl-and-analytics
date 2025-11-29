# Infrastructure

Terraform infrastructure-as-code for the Serverless Sales Data Platform.

## Directory Structure

```
infrastructure/
├── main.tf                    # Provider configuration + random bucket suffix
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── iam.tf                     # IAM roles and policies
├── lambda.tf                  # Lambda functions (17 functions)
├── api-gateway.tf             # API Gateway resources
├── s3.tf                      # S3 bucket configuration
├── eventbridge.tf             # EventBridge rules
├── step-functions.tf          # Step Functions state machines
├── dynamodb.tf                # DynamoDB tables
├── sns.tf                     # SNS topics for notifications
├── cloudwatch.tf              # CloudWatch log groups
├── quicksight.tf              # QuickSight resources (optional)
├── terraform.tfvars.example   # Example variable values (copy and customize)
└── *.tfvars                   # Your variable values (not in git)
```

## Resources Created

### Compute

| Resource | Count | Description |
|----------|-------|-------------|
| Lambda Functions | 17 | All processing functions (ARM64, Python 3.13) |
| Lambda Layer | 1 | AWS SDK Pandas layer reference |

### Storage

| Resource | Description |
|----------|-------------|
| S3 Bucket | Single bucket with prefixes: uploads/, processed/, rejected/, quicksight/ |
| DynamoDB Table | Single-table design for metrics, anomalies, trends, recommendations |

### Orchestration

| Resource | Description |
|----------|-------------|
| Step Functions | 2 state machines (upload-processor, daily-analysis) |
| EventBridge | Rule triggering on S3 uploads |

### API

| Resource | Description |
|----------|-------------|
| API Gateway | REST API with 5 endpoints |
| API Stage | Production stage (prod) |

### Messaging

| Resource | Description |
|----------|-------------|
| SNS Topic | Alerts and daily reports |
| SNS Subscription | Email subscription for alerts |

### Monitoring

| Resource | Description |
|----------|-------------|
| CloudWatch Log Groups | Logs for all Lambda functions and Step Functions |

## Quick Start

### Prerequisites

- Terraform >= 1.0
- AWS CLI configured
- Lambda functions built: `cd ../backend && ./build-all.sh`

### Configure Variables

```bash
# Copy the example file to create your own
cp terraform.tfvars.example myname-terraform.tfvars

# Edit with your values (s3_bucket_name and alert_email are required)
vim myname-terraform.tfvars
```

### Deploy

```bash
# Initialize (downloads providers including random)
terraform init

# Review changes
terraform plan -var-file="myname-terraform.tfvars" -out=tfplan

# Apply
terraform apply tfplan

# View outputs
terraform output
```

### Destroy

```bash
# Empty S3 bucket first
aws s3 rm s3://$(terraform output -raw s3_bucket_name) --recursive

# Destroy all resources
terraform destroy -var-file="myname-terraform.tfvars"
```

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `s3_bucket_name` | Base name for S3 bucket (random suffix appended automatically) |
| `alert_email` | Email address for SNS alerts and daily reports |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region | `us-east-1` |
| `frontend_origin` | Frontend URL for CORS | `http://localhost:3000` |
| `upload_prefix` | S3 prefix for uploads | `uploads/` |
| `processed_prefix` | S3 prefix for Parquet files | `processed/` |
| `rejected_prefix` | S3 prefix for rejected files | `rejected/` |
| `expected_stores` | Comma-separated store IDs | `0001,0002,...,0011` |
| `alert_phone` | Phone for SMS alerts (E.164) | `""` |
| `bedrock_model_id` | Bedrock model for AI | `amazon.nova-lite-v1:0` |
| `log_level` | Lambda log level | `INFO` |
| `enable_quicksight` | Enable QuickSight resources | `false` |
| `quicksight_user_arn` | QuickSight user ARN | `""` |
| `daily_analysis_schedule` | Cron for scheduled daily analysis (UTC) | `cron(0 23 * * ? *)` |
| `daily_analysis_timezone` | Timezone for "today" in analysis | `America/New_York` |
| `enable_scheduled_analysis` | Enable scheduled fallback trigger | `true` |

### S3 Bucket Naming

The S3 bucket name is automatically made globally unique by appending a random 7-character suffix:
- You provide: `my-sales-bucket`
- Final name: `my-sales-bucket-abc1234`

This prevents bucket name conflicts while keeping the name readable.

### Setting Variables

**Option 1: tfvars file (Recommended)**

```bash
# Create from example
cp terraform.tfvars.example myname-terraform.tfvars

# Run with your file
terraform plan -var-file="myname-terraform.tfvars"
terraform apply -var-file="myname-terraform.tfvars"
```

**Option 2: Command line**

```bash
terraform apply \
  -var="s3_bucket_name=my-bucket" \
  -var="alert_email=me@example.com"
```

**Option 3: Environment variables**

```bash
export TF_VAR_s3_bucket_name="my-bucket"
export TF_VAR_alert_email="me@example.com"
terraform apply
```

## Outputs

| Output | Description |
|--------|-------------|
| `api_gateway_url` | API Gateway endpoint URL |
| `s3_bucket_name` | S3 bucket name (with random suffix) |
| `s3_bucket_arn` | S3 bucket ARN |
| `upload_processor_arn` | Upload processor state machine ARN |
| `daily_analysis_arn` | Daily analysis state machine ARN |
| `dynamodb_table_name` | DynamoDB table name |
| `sns_topic_arn` | SNS alerts topic ARN |

### View Outputs

```bash
terraform output
terraform output api_gateway_url
terraform output -json
```

## File Descriptions

### main.tf

Provider configuration:
- AWS provider with region
- Required providers and versions (aws, archive, random)
- Random string resource for bucket suffix
- Local value for complete bucket name

### variables.tf

Input variable definitions:
- Required: `s3_bucket_name`, `alert_email`
- Optional with defaults
- Validation rules

### outputs.tf

Exported values for integration:
- API URLs
- Resource ARNs
- Bucket names

### iam.tf

IAM roles and policies:
- `lambda_role` - Execution role for all Lambda functions
- `step_function_role` - Execution role for Step Functions
- `eventbridge_role` - Role for EventBridge to invoke Step Functions

Policies grant:
- S3 read/write (all prefixes)
- DynamoDB read/write
- CloudWatch Logs
- SNS publish
- Bedrock invoke model
- Step Functions start execution

### lambda.tf

All 17 Lambda functions organized by phase:

**Phase 1: Upload ETL**
- generate-upload-url
- process-upload
- calculate-metrics
- write-metrics
- check-all-stores

**Phase 2: Daily Analysis**
- get-store-summaries
- calc-company-metrics
- calc-product-metrics
- detect-anomalies
- analyze-trends
- generate-recommendations
- combine-insights
- generate-report
- export-to-quicksight

**Phase 3: Data Access APIs**
- list-files
- generate-download-url
- get-analytics
- get-trends

Each function includes:
- `archive_file` data source for packaging
- Environment variables with configurable log level
- Lambda layer attachment (Powertools, Pandas where needed)
- Proper IAM role

### api-gateway.tf

REST API configuration:
- OpenAPI 3.0 specification
- Lambda integrations
- CORS configuration
- Production stage

### s3.tf

S3 bucket configuration:
- Uses `local.s3_bucket_name` (with random suffix)
- Server-side encryption (AES256)
- Versioning enabled
- Public access blocked
- CORS for frontend
- EventBridge notifications enabled

### eventbridge.tf

Event-driven triggers:
- Rule for S3 Object Created events targeting upload-processor Step Function
- Scheduled rule for daily analysis fallback (runs at configured time if not all stores reported)
- Input transformation for S3 event data
- trigger_daily_analysis Lambda for scheduled execution with timezone support and idempotency check

### step-functions.tf

State machine definitions:
- upload-processor workflow
- daily-analysis workflow
- Template substitution for Lambda ARNs
- CloudWatch logging

### dynamodb.tf

Single-table design:
- Partition key: PK (String)
- Sort key: SK (String)
- GSI1 for alternate access patterns
- On-demand capacity

### sns.tf

Notification configuration:
- Alerts topic for failures
- Daily reports topic
- Email subscription

### cloudwatch.tf

Logging configuration:
- Log groups for all Lambda functions
- Log groups for Step Functions
- 14-day retention

### quicksight.tf

QuickSight resources (optional):
- Data source pointing to S3
- Datasets for store summaries, products, anomalies, trends, recommendations
- Dashboard definitions

## Development Workflow

### Making Changes

```bash
# Format code
terraform fmt

# Validate syntax
terraform validate

# Review changes
terraform plan -var-file="myname-terraform.tfvars" -out=tfplan

# Apply changes
terraform apply tfplan
```

### Targeted Updates

```bash
# Update specific resource
terraform apply -var-file="myname-terraform.tfvars" -target=aws_lambda_function.process_upload

# Update all Lambda functions
terraform apply -var-file="myname-terraform.tfvars" -target=module.lambda
```

### State Management

```bash
# View state
terraform show

# List resources
terraform state list

# Import existing resource
terraform import aws_lambda_function.process_upload process_upload

# Refresh from AWS
terraform refresh
```

## Remote State (Production)

For team collaboration:

```hcl
# main.tf
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "serverless-etl/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

## Troubleshooting

### Lambda Package Not Found

```bash
# Build functions first
cd ../backend
./build-all.sh
cd ../infrastructure
terraform apply -var-file="myname-terraform.tfvars"
```

### Missing Required Variables

```
Error: No value for required variable
```

Ensure you're using a var-file or have set the required variables:
- `s3_bucket_name`
- `alert_email`

### State Lock Error

```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

### Resource Drift

```bash
# Refresh state from AWS
terraform refresh -var-file="myname-terraform.tfvars"

# View differences
terraform plan -var-file="myname-terraform.tfvars"
```

## Cost Estimation

Monthly costs (estimated for light usage):

| Service | Estimated Cost |
|---------|---------------|
| Lambda | ~$0.50 |
| API Gateway | ~$0.50 |
| S3 | ~$0.50 |
| DynamoDB | ~$1.00 |
| Step Functions | ~$0.50 |
| CloudWatch | ~$1.00 |
| Bedrock (Nova Lite) | ~$5.00 |
| **Total** | **~$9.00/month** |

QuickSight adds ~$24/month for author access.

Use AWS Cost Explorer for actual costs.

## Related Documentation

- [Project Overview](../README.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Diagrams](../docs/DIAGRAMS.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Backend Components](../backend/README.md)
