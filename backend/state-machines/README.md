# Step Functions State Machines

This directory contains AWS Step Functions state machine definitions for orchestrating serverless workflows.

## Overview

Step Functions provides serverless workflow orchestration for AWS services. State machines in this directory define the workflow logic, retry policies, error handling, and state transitions.

## State Machines

### daily-analysis.json

**Purpose:** Runs daily aggregation, AI-powered anomaly detection, trend analysis, and generates recommendations using Amazon Bedrock. Exports data to QuickSight and sends daily email reports.

**Workflow:**
```
Start
  ↓
GetStoreSummaries ──→ CheckStoreSummaries
                           ↓
                    (No data?) → NoDataAvailable → FailNoData
                           ↓
                    CalcCompanyMetrics
                           ↓
                    CalcProductMetrics
                           ↓
                    BedrockAnalysis (Parallel)
                    ├── DetectAnomalies (Bedrock)
                    └── AnalyzeTrends (Bedrock)
                           ↓
                    GenerateRecommendations (Bedrock)
                           ↓
                    CombineInsights
                           ↓
                    CheckForBedrockErrors
                           ↓ (if errors)
                    SendBedrockErrorAlert (optional)
                           ↓
                    GenerateReport
                           ↓
                    SendDailyReport (SNS)
                           ↓
                    ExportToQuickSight
                           ↓
                    Success
```

**States:**

1. **GetStoreSummaries** - Fetches all store metrics for the specified date from DynamoDB
2. **CheckStoreSummaries** - Choice state: fails if no data available
3. **CalcCompanyMetrics** - Aggregates metrics across all stores
4. **CalcProductMetrics** - Calculates product-level metrics (top sellers, etc.)
5. **BedrockAnalysis** - Parallel execution:
   - **DetectAnomalies** - Uses Bedrock to identify unusual patterns vs historical data
   - **AnalyzeTrends** - Uses Bedrock to analyze sales trends
6. **GenerateRecommendations** - Uses Bedrock to generate actionable recommendations
7. **CombineInsights** - Merges all AI analysis results
8. **CheckForBedrockErrors** - Sends alert if any Bedrock calls partially failed
9. **GenerateReport** - Formats the daily report for email
10. **SendDailyReport** - Publishes report to SNS topic
11. **ExportToQuickSight** - Exports NDJSON files for QuickSight dashboards

**Trigger:** Manual execution or scheduled (e.g., via EventBridge scheduled rule)

**Input Format:**
```json
{
  "date": "2025-01-15"
}
```

**Error Handling:**
- Each Lambda task has retry with exponential backoff (3 attempts)
- Bedrock tasks have additional retry for throttling errors
- Partial failures (e.g., one Bedrock call fails) continue with available data
- Critical failures send SNS alert and mark execution as FAILED

**Template Variables:**
- `${get_store_summaries_lambda_arn}`
- `${calc_company_metrics_lambda_arn}`
- `${calc_product_metrics_lambda_arn}`
- `${detect_anomalies_lambda_arn}`
- `${analyze_trends_lambda_arn}`
- `${generate_recommendations_lambda_arn}`
- `${combine_insights_lambda_arn}`
- `${generate_report_lambda_arn}`
- `${export_to_quicksight_lambda_arn}`
- `${sns_alerts_topic_arn}`
- `${sns_daily_report_topic_arn}`

---

### upload-processor.json

**Purpose:** Orchestrates the processing of uploaded JSON files by invoking the ETL Lambda function with built-in retry logic.

**Workflow:**
```
Start → LogInput (Pass) → ProcessUpload (Task) → End
```

**States:**

1. **LogInput** (Pass State)
   - Type: Pass
   - Purpose: Logs the input event for debugging
   - ResultPath: `$.logging`
   - Next: ProcessUpload

2. **ProcessUpload** (Task State)
   - Type: Task
   - Resource: Lambda function `process_upload`
   - Retry Configuration:
     - Max Attempts: 3
     - Interval: 2 seconds
     - Backoff Rate: 2x (exponential)
     - Error Types: ALL
   - End: true

**Trigger:** EventBridge rule on S3 Object Created events

**Input Format:**
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

**Retry Behavior:**
- Attempt 1: Immediate
- Attempt 2: After 2 seconds
- Attempt 3: After 4 seconds (2 × 2)
- Total max duration: ~6 seconds (plus Lambda execution time)

**Error Handling:**
- Retries on all error types
- After 3 failed attempts, execution marked as FAILED
- CloudWatch Logs capture all execution details

## File Format

State machine definitions use Amazon States Language (ASL), a JSON-based language for defining state machines.

**Key Concepts:**
- **States:** Individual steps in the workflow
- **Transitions:** Connections between states
- **Retry:** Automatic retry on failures
- **Catch:** Error handling and fallback logic
- **Choice:** Conditional branching
- **Parallel:** Execute multiple branches simultaneously
- **Map:** Iterate over array items

## Terraform Integration

State machines are deployed via Terraform using `templatefile()`:

```terraform
resource "aws_sfn_state_machine" "upload_processor" {
  name     = "upload-processor"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/../backend/state-machines/upload-processor.json", {
    process_upload_lambda_arn = aws_lambda_function.process_upload.arn
  })
}
```

**Template Variables:**
- `${process_upload_lambda_arn}` - Dynamically injected Lambda ARN

This allows the state machine to reference resources created by Terraform.

## Testing State Machines

### Local Testing with AWS SAM

While Step Functions don't run locally, you can validate syntax:

```bash
# Validate JSON syntax
cat upload-processor.json | jq .

# Use AWS SAM to test locally (requires Docker)
sam local start-stepfunctions-api
```

### Testing in AWS Console

1. Navigate to Step Functions console
2. Select `upload-processor` state machine
3. Click "Start execution"
4. Provide test input:
```json
{
  "detail": {
    "bucket": {"name": "<your-bucket-name>"},
    "object": {"key": "uploads/test.json"}
  }
}
```
5. View execution graph and logs

### Testing with AWS CLI

```bash
# Start execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:upload-processor \
  --input '{"detail":{"bucket":{"name":"<your-bucket-name>"},"object":{"key":"uploads/test.json"}}}'

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:upload-processor

# Get execution details
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:us-east-1:ACCOUNT:execution:upload-processor:EXECUTION_ID
```

## Monitoring

### CloudWatch Metrics

Step Functions automatically publishes metrics:
- `ExecutionsFailed` - Number of failed executions
- `ExecutionsSucceeded` - Number of successful executions
- `ExecutionTime` - Duration of executions
- `ExecutionThrottled` - Number of throttled executions

### CloudWatch Logs

Enable logging in Terraform for detailed execution logs:
```terraform
resource "aws_sfn_state_machine" "upload_processor" {
  # ... other config ...

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}
```

### X-Ray Tracing

Enable X-Ray for distributed tracing:
```terraform
resource "aws_sfn_state_machine" "upload_processor" {
  # ... other config ...

  tracing_configuration {
    enabled = true
  }
}
```

## State Machine Patterns

### Error Handling

**Retry with Exponential Backoff:**
```json
{
  "Retry": [{
    "ErrorEquals": ["States.ALL"],
    "IntervalSeconds": 2,
    "MaxAttempts": 3,
    "BackoffRate": 2
  }]
}
```

**Catch and Handle Errors:**
```json
{
  "Catch": [{
    "ErrorEquals": ["States.ALL"],
    "Next": "HandleError"
  }]
}
```

### Parallel Processing

```json
{
  "Type": "Parallel",
  "Branches": [
    {
      "StartAt": "ProcessJSON",
      "States": { ... }
    },
    {
      "StartAt": "ProcessCSV",
      "States": { ... }
    }
  ]
}
```

### Conditional Logic

```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.fileType",
      "StringEquals": "json",
      "Next": "ProcessJSON"
    },
    {
      "Variable": "$.fileType",
      "StringEquals": "csv",
      "Next": "ProcessCSV"
    }
  ],
  "Default": "UnsupportedFormat"
}
```

## Adding New State Machines

1. **Create definition file:**
   ```bash
   cd backend/state-machines
   touch my-new-workflow.json
   ```

2. **Define workflow:**
   ```json
   {
     "Comment": "My new workflow",
     "StartAt": "FirstState",
     "States": {
       "FirstState": {
         "Type": "Task",
         "Resource": "${lambda_arn}",
         "End": true
       }
     }
   }
   ```

3. **Add to Terraform:**
   ```terraform
   resource "aws_sfn_state_machine" "my_workflow" {
     name     = "my-workflow"
     role_arn = aws_iam_role.step_function_role.arn

     definition = templatefile(
       "${path.module}/../backend/state-machines/my-new-workflow.json",
       {
         lambda_arn = aws_lambda_function.my_function.arn
       }
     )
   }
   ```

4. **Deploy:**
   ```bash
   cd infrastructure
   terraform apply
   ```

## Best Practices

### State Machine Design
- **Keep it simple:** Start with simple workflows, add complexity as needed
- **Use Pass states:** For debugging and logging intermediate data
- **Set timeouts:** Prevent runaway executions
- **Use Choice sparingly:** Too many branches make workflows hard to understand

### Error Handling
- **Always add retry:** Even for "reliable" services
- **Use exponential backoff:** Prevents overwhelming downstream services
- **Catch errors gracefully:** Provide fallback paths
- **Log failures:** Enable CloudWatch Logs for debugging

### Performance
- **Limit state transitions:** Each transition costs money
- **Batch when possible:** Use Map state for parallel processing
- **Set appropriate timeouts:** Don't wait longer than necessary
- **Use Express workflows:** For high-volume, short-duration workloads

### Security
- **Principle of least privilege:** State machine role should have minimal permissions
- **Don't log sensitive data:** Use `ResultPath: null` to exclude data
- **Encrypt state data:** Use AWS KMS for sensitive workflows
- **Use VPC endpoints:** For private network access

## Troubleshooting

### Execution Failed

**Check CloudWatch Logs:**
```bash
aws logs tail /aws/stepfunctions/upload-processor --follow
```

**Common Issues:**
- Lambda timeout exceeded
- Invalid input format
- Missing IAM permissions
- Resource not found

### Execution Stuck

**Check state timeout:**
```json
{
  "TimeoutSeconds": 300
}
```

**Check task heartbeat:**
```json
{
  "HeartbeatSeconds": 60
}
```

### Invalid Definition

**Validate JSON:**
```bash
cat upload-processor.json | jq .
```

**Common syntax errors:**
- Missing comma between states
- Undefined state in "Next" field
- Invalid state type
- Circular state references

## Cost Optimization

**Step Functions Pricing (as of 2025):**
- Standard: $0.025 per 1,000 state transitions
- Express: $1.00 per 1 million requests + duration charges

**Optimization Tips:**
1. **Use Express for high-volume:** If >1000 executions/second
2. **Minimize states:** Combine simple operations
3. **Set short timeouts:** Don't pay for waiting
4. **Use Lambda efficiently:** Minimize Step Functions → Lambda overhead

## Resources

- [AWS Step Functions Developer Guide](https://docs.aws.amazon.com/step-functions/)
- [Amazon States Language Spec](https://states-language.net/spec.html)
- [Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/bp-express.html)
- [Step Functions Patterns](https://serverlessland.com/patterns?services=sfn)
- [Workflow Studio](https://aws.amazon.com/step-functions/features/#Workflow_Studio) - Visual editor

## Related Files

- Lambda Functions: [../functions/](../functions/)
- Infrastructure: [../../infrastructure/](../../infrastructure/)
- Architecture Docs: [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)
- Deployment Guide: [../../docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md)
