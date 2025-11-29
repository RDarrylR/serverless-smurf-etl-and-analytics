# EventBridge

# EventBridge rule to capture S3 upload events
resource "aws_cloudwatch_event_rule" "s3_upload" {
  name        = "capture-s3-uploads"
  description = "Capture all S3 object uploads"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.upload_bucket.id]
      }
      object = {
        key = [{
          prefix = var.upload_prefix
        }]
      }
    }
  })

  depends_on = [aws_cloudwatch_log_group.eventbridge_logs]
}

# EventBridge target: Trigger Step Functions on S3 upload
resource "aws_cloudwatch_event_target" "step_function" {
  rule      = aws_cloudwatch_event_rule.s3_upload.name
  target_id = "UploadProcessorStepFunction"
  arn       = aws_sfn_state_machine.upload_processor.arn
  role_arn  = aws_iam_role.eventbridge_step_function_role.arn

  # Transform S3 event to Step Functions input format
  input_transformer {
    input_paths = {
      bucket = "$.detail.bucket.name"
      key    = "$.detail.object.key"
    }
    input_template = <<EOF
    {
      "detail": {
        "bucket": {
          "name": <bucket>
        },
        "object": {
          "key": <key>
        }
      }
    }
    EOF
  }
}

# EventBridge rule for scheduled daily analysis (runs even if not all stores reported)
resource "aws_cloudwatch_event_rule" "scheduled_daily_analysis" {
  count = var.enable_scheduled_analysis ? 1 : 0

  name                = "scheduled-daily-analysis"
  description         = "Trigger daily analysis at scheduled time even if not all stores have reported"
  schedule_expression = var.daily_analysis_schedule
}

# EventBridge target: Use Lambda to trigger daily analysis with current date
# (EventBridge doesn't support dynamic date substitution in input)
resource "aws_cloudwatch_event_target" "scheduled_daily_analysis" {
  count = var.enable_scheduled_analysis ? 1 : 0

  rule      = aws_cloudwatch_event_rule.scheduled_daily_analysis[0].name
  target_id = "ScheduledDailyAnalysisLambda"
  arn       = aws_lambda_function.trigger_daily_analysis[0].arn
}

# Lambda function to trigger daily analysis with current date
data "archive_file" "trigger_daily_analysis_zip" {
  count = var.enable_scheduled_analysis ? 1 : 0

  type        = "zip"
  output_path = "${path.module}/../backend/functions/trigger-daily-analysis.zip"

  source {
    content  = <<EOF
import boto3
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')
TIMEZONE = os.environ.get('TIMEZONE', 'America/New_York')

def lambda_handler(event, context):
    sfn = boto3.client('stepfunctions')

    # Get today's date in the configured local timezone
    local_tz = ZoneInfo(TIMEZONE)
    today = datetime.now(local_tz).strftime('%Y-%m-%d')

    print(f"Checking daily analysis for {today} (timezone: {TIMEZONE})")

    # Check if daily analysis already ran successfully today
    # Look for executions that started today and succeeded
    executions = sfn.list_executions(
        stateMachineArn=STATE_MACHINE_ARN,
        statusFilter='SUCCEEDED',
        maxResults=20
    )

    for execution in executions.get('executions', []):
        # Check if this execution was for today's date by looking at the input
        # Get execution details to check the date in the input
        exec_detail = sfn.describe_execution(executionArn=execution['executionArn'])
        try:
            exec_input = json.loads(exec_detail.get('input', '{}'))
            exec_date = exec_input.get('date', '')
            if exec_date == today:
                # An execution already succeeded for today's date, skip
                print(f"Daily analysis already completed for {today} (execution: {execution['executionArn']})")
                return {
                    'statusCode': 200,
                    'message': 'Daily analysis already completed for today',
                    'skipped': True,
                    'date': today,
                    'existingExecutionArn': execution['executionArn']
                }
        except (json.JSONDecodeError, KeyError):
            continue

    # No successful execution found for today, start a new one
    print(f"Starting scheduled daily analysis for {today}")
    response = sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps({
            'date': today,
            'triggered_by': 'scheduled'
        })
    )

    return {
        'statusCode': 200,
        'message': 'Daily analysis started',
        'skipped': False,
        'executionArn': response['executionArn'],
        'date': today
    }
EOF
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "trigger_daily_analysis" {
  count = var.enable_scheduled_analysis ? 1 : 0

  filename         = data.archive_file.trigger_daily_analysis_zip[0].output_path
  function_name    = "trigger_daily_analysis"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 128
  source_code_hash = data.archive_file.trigger_daily_analysis_zip[0].output_base64sha256

  environment {
    variables = {
      STATE_MACHINE_ARN = aws_sfn_state_machine.daily_analysis.arn
      TIMEZONE          = var.daily_analysis_timezone
    }
  }
}

# Permission for EventBridge to invoke the Lambda
resource "aws_lambda_permission" "allow_eventbridge_trigger_daily" {
  count = var.enable_scheduled_analysis ? 1 : 0

  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger_daily_analysis[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scheduled_daily_analysis[0].arn
}
