# CloudWatch

# CloudWatch Log Group for EventBridge logs
resource "aws_cloudwatch_log_group" "eventbridge_logs" {
  name              = "/aws/events/s3-uploads"
  retention_in_days = 14
}

# =============================================================================
# CloudWatch Alarms for Lambda Functions
# =============================================================================

# Alarm for any Lambda errors across all functions
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "sales-platform-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Triggered when any Lambda function in the sales platform has errors"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.sales_alerts.arn]
  ok_actions    = [aws_sns_topic.sales_alerts.arn]

  dimensions = {}
}

# Alarm for Lambda throttling
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "sales-platform-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Triggered when any Lambda function is throttled"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.sales_alerts.arn]

  dimensions = {}
}

# Alarm for process_upload function duration (approaching timeout)
resource "aws_cloudwatch_metric_alarm" "process_upload_duration" {
  alarm_name          = "sales-platform-process-upload-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 24000 # 24 seconds (80% of 30s timeout)
  alarm_description   = "Triggered when process_upload Lambda is approaching timeout"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.sales_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.process_upload.function_name
  }
}

# Alarm for Bedrock functions duration (approaching timeout)
resource "aws_cloudwatch_metric_alarm" "bedrock_functions_duration" {
  alarm_name          = "sales-platform-bedrock-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 48000 # 48 seconds (80% of 60s timeout)
  alarm_description   = "Triggered when Bedrock analysis functions are approaching timeout"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.sales_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.detect_anomalies.function_name
  }
}

# =============================================================================
# CloudWatch Alarms for Step Functions
# =============================================================================

# Alarm for Step Functions execution failures
resource "aws_cloudwatch_metric_alarm" "step_functions_failed" {
  alarm_name          = "sales-platform-step-functions-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Triggered when any Step Functions execution fails"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.sales_alerts.arn]

  dimensions = {}
}

# Alarm for Step Functions execution timeout
resource "aws_cloudwatch_metric_alarm" "step_functions_timeout" {
  alarm_name          = "sales-platform-step-functions-timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsTimedOut"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Triggered when any Step Functions execution times out"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.sales_alerts.arn]

  dimensions = {}
}

# =============================================================================
# CloudWatch Alarms for DynamoDB
# =============================================================================

# Alarm for DynamoDB throttled requests
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttled" {
  alarm_name          = "sales-platform-dynamodb-throttled"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Triggered when DynamoDB requests are throttled"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.sales_alerts.arn]

  dimensions = {
    TableName = aws_dynamodb_table.sales_data.name
  }
}
