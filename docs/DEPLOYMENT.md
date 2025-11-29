# Deployment Guide

This project uses **Terraform** for infrastructure-as-code deployment to AWS.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Build Lambda Functions](#build-lambda-functions)
- [Deploy Infrastructure](#deploy-infrastructure)
- [Configure Frontend](#configure-frontend)
- [Verify Deployment](#verify-deployment)
- [Update Deployment](#update-deployment)
- [Destroy Infrastructure](#destroy-infrastructure)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

| Tool | Version | Installation |
|------|---------|--------------|
| AWS CLI | >= 2.0 | `brew install awscli` |
| Terraform | >= 1.0 | `brew install terraform` |
| Python | 3.13 | `brew install python@3.13` |
| Node.js | >= 18 | `brew install node` |

### AWS Configuration

```bash
# Configure AWS credentials
aws configure

# Verify access
aws sts get-caller-identity
```

Required IAM permissions:
- Lambda (full access)
- API Gateway (full access)
- S3 (full access)
- Step Functions (full access)
- EventBridge (full access)
- DynamoDB (full access)
- SNS (full access)
- Bedrock (invoke model)
- IAM (create roles/policies)
- CloudWatch (logs, metrics)

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd serverless-file-upload-etl

# 2. Build all Lambda functions
cd backend && ./build-all.sh && cd ..

# 3. Configure your variables
cd infrastructure
cp terraform.tfvars.example myname-terraform.tfvars
# Edit myname-terraform.tfvars with your s3_bucket_name and alert_email

# 4. Deploy infrastructure
terraform init
terraform plan -var-file="myname-terraform.tfvars" -out=tfplan
terraform apply tfplan

# 5. Configure and start frontend
cd ../frontend
cp .env.example .env
# Edit .env with API Gateway URL from terraform output
npm install && npm start
```

## Build Lambda Functions

All Lambda functions must be built before deployment. The build scripts create deployment packages with Python dependencies compiled for Linux ARM64.

### Build All Functions

```bash
cd backend
./build-all.sh
```

This builds all 17 Lambda functions:

**Phase 1: Upload ETL**
- `generate-upload-url` - Presigned URL generation
- `process-upload` - JSON validation and Parquet conversion
- `calculate-metrics` - Store-level metrics calculation
- `write-metrics` - DynamoDB metrics writer
- `check-all-stores` - Daily completion checker

**Phase 2: Daily Analysis**
- `aggregate-daily` - Cross-store aggregation
- `detect-anomalies` - Statistical anomaly detection
- `analyze-trends` - Time series trend analysis
- `generate-recommendations` - AI-powered recommendations (Bedrock)
- `format-report` - Report formatting
- `send-report` - SNS email delivery
- `export-to-quicksight` - NDJSON export for QuickSight

**Phase 3: Data Access APIs**
- `list-files` - List uploaded files
- `get-metrics` - Retrieve store metrics
- `get-recommendations` - Get AI recommendations
- `download-file` - Download processed Parquet files

### Build Individual Function

```bash
cd backend/functions/<function-name>
./build.sh
```

### Build Output

Each function creates a deployment package:
```
backend/functions/
├── generate-upload-url/
│   └── package/           # Deployment package
├── process-upload/
│   └── package/           # Deployment package with dependencies
└── ...
```

## Deploy Infrastructure

### Initialize Terraform

```bash
cd infrastructure
terraform init
```

This downloads providers and initializes the backend.

### Review Changes

```bash
terraform plan -var-file="myname-terraform.tfvars" -out=tfplan
```

Review the execution plan showing:
- Resources to be created
- Resources to be modified
- Resources to be destroyed

### Apply Changes

```bash
terraform apply tfplan
```

**Expected output:**
```
Apply complete! Resources: 45 added, 0 changed, 0 destroyed.

Outputs:

api_gateway_url = "https://abc123.execute-api.us-east-1.amazonaws.com/prod"
s3_bucket_name = "my-sales-uploads-abc1234"
upload_processor_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:upload-processor"
daily_analysis_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:daily-analysis"
```

Note: The S3 bucket name will have a random 7-character suffix appended automatically.

### Configuration Variables

Copy the example file and customize:

```bash
cp terraform.tfvars.example myname-terraform.tfvars
```

Edit your tfvars file:

```hcl
# Required variables
s3_bucket_name = "my-sales-uploads"
alert_email    = "alerts@example.com"

# Optional variables
aws_region      = "us-east-1"
frontend_origin = "http://localhost:3000"
log_level       = "INFO"
```

| Variable | Description | Default |
|----------|-------------|---------|
| `s3_bucket_name` | Base S3 bucket name (random suffix added) | **Required** |
| `alert_email` | Email for SNS alerts | **Required** |
| `aws_region` | AWS region | `us-east-1` |
| `frontend_origin` | Frontend URL for CORS | `http://localhost:3000` |
| `log_level` | Lambda log level | `INFO` |
| `enable_quicksight` | Enable QuickSight resources | `false` |
| `daily_analysis_schedule` | Cron for scheduled analysis (UTC) | `cron(0 23 * * ? *)` |
| `daily_analysis_timezone` | Timezone for "today" determination | `America/New_York` |
| `enable_scheduled_analysis` | Enable scheduled fallback trigger | `true` |

### Remote State (Recommended for Production)

Configure S3 backend for team collaboration:

```hcl
# main.tf
terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "serverless-etl/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

## Configure Frontend

### Environment Configuration

```bash
cd frontend

# Configure API URL automatically from Terraform output
./configure-api.sh
```

### Build and Deploy Frontend

**Development:**
```bash
cd frontend
npm install
./configure-api.sh
npm start
```

**Production Build:**
```bash
npm run build
# Deploy build/ directory to S3, CloudFront, or other hosting
```

## Verify Deployment

### Check Resources

```bash
# Verify Lambda functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `smurf`)].FunctionName'

# Verify Step Functions
aws stepfunctions list-state-machines --query 'stateMachines[].name'

# Verify DynamoDB table
aws dynamodb describe-table --table-name sales-metrics --query 'Table.TableStatus'

# Verify S3 bucket
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/
```

### Test Upload Pipeline

```bash
# Upload a test file
cd scripts
python3 generate_sample_data.py  # Generate sample data first
./upload_sample_data.sh --days 1 --delay 0

# Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn $(terraform output -raw upload_processor_arn) \
  --max-results 5
```

### Check Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/process_upload --follow

# Step Functions logs
aws logs tail /aws/stepfunctions/upload-processor --follow
```

## Update Deployment

### Code Changes

After modifying Lambda function code:

```bash
# 1. Rebuild affected functions
cd backend
./build-all.sh  # Or ./functions/<name>/build.sh for specific function

# 2. Apply Terraform changes
cd ../infrastructure
terraform plan -out=tfplan
terraform apply tfplan
```

### Infrastructure Changes

After modifying Terraform configuration:

```bash
cd infrastructure
terraform fmt      # Format code
terraform validate # Validate syntax
terraform plan -out=tfplan
terraform apply tfplan
```

### State Machine Changes

After modifying Step Functions definitions:

```bash
cd infrastructure
terraform apply -target=aws_sfn_state_machine.upload_processor
terraform apply -target=aws_sfn_state_machine.daily_analysis
```

## Destroy Infrastructure

### Full Teardown

```bash
cd infrastructure
terraform destroy
```

**Warning:** This deletes all resources including:
- S3 bucket (must be empty first)
- DynamoDB tables (data will be lost)
- Lambda functions
- Step Functions state machines
- All logs and metrics

### Empty S3 Bucket First

```bash
# Delete all objects
aws s3 rm s3://$(terraform output -raw s3_bucket_name) --recursive

# Then destroy
terraform destroy
```

### Selective Destruction

```bash
# Destroy specific resources
terraform destroy -target=aws_lambda_function.process_upload
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
      - 'infrastructure/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Build Lambda Functions
        run: |
          cd backend
          ./build-all.sh

      - name: Terraform Init
        run: |
          cd infrastructure
          terraform init

      - name: Terraform Plan
        run: |
          cd infrastructure
          terraform plan -out=tfplan

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: |
          cd infrastructure
          terraform apply -auto-approve tfplan
```

### Pre-commit Hooks

```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.83.5
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_docs
```

## Troubleshooting

### Build Failures

**Issue:** `build.sh` fails with pip errors

```bash
# Check Python version
python3 --version  # Should be 3.13

# Install pip
python3 -m ensurepip --upgrade

# Retry build
./build.sh
```

**Issue:** Missing dependencies

```bash
# Clean and rebuild
rm -rf package/
./build.sh
```

### Deployment Failures

**Issue:** S3 bucket already exists

```bash
# Use a unique bucket name
terraform apply -var="s3_bucket_name=my-unique-bucket-$(date +%s)"
```

**Issue:** Lambda deployment package not found

```bash
# Build functions first
cd backend
./build-all.sh
cd ../infrastructure
terraform apply
```

**Issue:** IAM permission errors

```bash
# Check current user permissions
aws iam get-user

# Verify required permissions exist
aws iam list-attached-user-policies --user-name <your-user>
```

### Runtime Failures

**Issue:** Lambda timeout

```bash
# Check CloudWatch logs
aws logs tail /aws/lambda/<function-name> --follow

# Increase timeout in Terraform if needed
# Edit infrastructure/lambda.tf
```

**Issue:** Step Function execution failed

```bash
# Get execution details
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn <execution-arn>
```

### State Issues

**Issue:** Terraform state out of sync

```bash
# Refresh state from AWS
terraform refresh

# Import missing resources
terraform import aws_lambda_function.process_upload process_upload
```

**Issue:** State lock errors

```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

## Resources

### Documentation

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/)
- [AWS Step Functions Guide](https://docs.aws.amazon.com/step-functions/latest/dg/)
- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/)

### Project Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [System Diagrams](DIAGRAMS.md)
- [Backend Components](../backend/README.md)
- [Infrastructure Details](../infrastructure/README.md)
