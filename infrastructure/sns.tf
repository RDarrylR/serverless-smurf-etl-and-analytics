# SNS Topics for Sales Data Platform

# Alerts topic - for rejection alerts, missing store alerts, critical anomalies
resource "aws_sns_topic" "sales_alerts" {
  name = "sales-alerts"

  tags = {
    Name        = "sales-alerts"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# Daily report topic - for daily summary reports
resource "aws_sns_topic" "sales_daily_report" {
  name = "sales-daily-report"

  tags = {
    Name        = "sales-daily-report"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# Email subscription for alerts (if email provided)
resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.sales_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Email subscription for daily reports (if email provided)
resource "aws_sns_topic_subscription" "daily_report_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.sales_daily_report.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# SMS subscription for alerts (if phone provided)
resource "aws_sns_topic_subscription" "alerts_sms" {
  count     = var.alert_phone != "" ? 1 : 0
  topic_arn = aws_sns_topic.sales_alerts.arn
  protocol  = "sms"
  endpoint  = var.alert_phone
}

# Outputs
output "sns_alerts_topic_arn" {
  description = "ARN of the sales alerts SNS topic"
  value       = aws_sns_topic.sales_alerts.arn
}

output "sns_daily_report_topic_arn" {
  description = "ARN of the daily report SNS topic"
  value       = aws_sns_topic.sales_daily_report.arn
}
