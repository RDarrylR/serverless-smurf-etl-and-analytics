# QuickSight Dashboard Setup

This directory contains the configuration and setup scripts for the Sales Data Platform QuickSight dashboard.

## Prerequisites

1. AWS Account with QuickSight enabled
2. QuickSight Enterprise Edition (for SPICE and scheduled refresh)
3. AWS CLI configured with appropriate permissions
4. Terraform applied with `enable_quicksight = true`

## Setup Steps

### Step 1: Subscribe to QuickSight

If you haven't already subscribed to QuickSight:

```bash
# Check current subscription status
./setup-quicksight.sh check

# Set up QuickSight subscription (Enterprise Edition)
export NOTIFICATION_EMAIL="your-email@example.com"
./setup-quicksight.sh setup
```

Or manually via AWS Console:
1. Go to AWS Console > QuickSight
2. Click "Sign up for QuickSight"
3. Choose "Enterprise" edition
4. Configure account settings

### Step 2: Create QuickSight User

```bash
# Register an IAM user in QuickSight
./setup-quicksight.sh register-user your-email@example.com your-iam-username ADMIN

# List QuickSight users and get ARN
./setup-quicksight.sh list-users
./setup-quicksight.sh get-user-arn your-username
```

### Step 3: Update Terraform Variables

Add to your `terraform.tfvars`:

```hcl
enable_quicksight   = true
quicksight_user_arn = "arn:aws:quicksight:us-east-1:123456789012:user/default/your-username"
```

### Step 4: Apply Terraform

```bash
cd infrastructure
terraform plan
terraform apply
```

This will create:
- 5 Data Sources (Store Summaries, Top Products, Anomalies, Trends, Recommendations)
- 5 Datasets with SPICE import mode
- 5 Daily refresh schedules (6:00 AM UTC)

### Step 5: Generate Sample Data

Upload store files through the frontend or API to trigger the ETL pipeline:

```bash
# Example: Upload a test file
curl -X POST "https://your-api.execute-api.us-east-1.amazonaws.com/prod/generate-upload-url" \
  -H "Content-Type: application/json" \
  -d '{"filename": "store_0001_2025-01-15.json"}'
```

After all expected stores upload (or the scheduled trigger runs), the daily analysis workflow will run and the export-to-quicksight Lambda will populate the S3 data.

### Step 6: Create Analysis and Dashboard

QuickSight analyses and dashboards are best created via the console. The `dashboard-definition.json` file provides a reference for the visualizations to create.

#### Executive Summary Sheet
- KPIs: Total Sales, Total Transactions, Avg Transaction Value, Active Stores
- Line Chart: Daily Sales Trend
- Bar Chart: Sales by Store
- Pie Chart: Payment Method Distribution

#### Store Performance Sheet
- Table: Store Performance Summary
- Heat Map: Store Sales by Day
- Bar Chart: Store Comparison (Sales vs Transactions)
- Line Chart: Store Sales Trend by Store

#### Product Analysis Sheet
- Table: Top Products by Revenue
- Bar Chart: Top 10 Products by Revenue
- Stacked Bar: Product Sales by Store
- Scatter Plot: Units Sold vs Revenue

#### AI Insights Sheet
- KPIs: Anomaly Count, Trends Identified, Recommendations
- Table: Recent Anomalies
- Bar Chart: Anomalies by Severity
- Table: Identified Trends
- Pie Chart: Trends by Type
- Table: Action Recommendations
- Bar Chart: Recommendations by Category

## File Structure

```
quicksight/
├── README.md                   # This file
├── setup-quicksight.sh         # Setup helper script
└── dashboard-definition.json   # Dashboard visualization reference
```

## Data Flow

```
DynamoDB Tables
      ↓
export-to-quicksight Lambda (runs after daily analysis)
      ↓
S3: quicksight/
├── store_summaries/*.parquet
├── top_products/*.parquet
├── anomalies/*.parquet
├── trends/*.parquet
└── recommendations/*.parquet
      ↓
QuickSight Data Sources (read from S3 manifests)
      ↓
QuickSight Datasets (SPICE import)
      ↓
QuickSight Analysis/Dashboard
```

## Refresh Schedule

Datasets are configured to refresh daily at 6:00 AM UTC. This runs after the typical overnight batch processing completes.

To manually refresh a dataset:
```bash
aws quicksight create-ingestion \
  --aws-account-id 123456789012 \
  --data-set-id sales-store-summaries-dataset \
  --ingestion-id "manual-refresh-$(date +%Y%m%d%H%M%S)"
```

## Troubleshooting

### No Data in Dashboard
1. Check if data exists in S3: `aws s3 ls s3://your-bucket/quicksight/`
2. Check manifest files exist: `aws s3 cat s3://your-bucket/quicksight/store_summaries/manifest.json`
3. Check dataset ingestion status in QuickSight console

### Refresh Failures
1. Check CloudWatch logs for export-to-quicksight Lambda
2. Verify IAM role permissions: `arn:aws:iam::123456789012:role/quicksight-s3-access-role`
3. Check SPICE capacity in QuickSight settings

### Permission Errors
1. Verify quicksight_user_arn is correct
2. Check that the QuickSight user has Author/Admin role
3. Ensure IAM role has S3 read access to the bucket

## Cost Considerations

- QuickSight Enterprise: ~$18/user/month (authors), ~$5/user/month (readers)
- SPICE capacity: 10GB included, then ~$0.25/GB/month
- Data refresh: No additional cost

## Security

- Data is encrypted at rest in S3 (SSE-S3)
- QuickSight accesses S3 via IAM role with least-privilege policy
- Dashboard access controlled through QuickSight user/group permissions
