# IAM Roles and Policies

# Lambda IAM role
resource "aws_iam_role" "lambda_role" {
  name = "file_upload_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda S3 access policy
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "lambda_s3_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:PutObjectAcl"
        ]
        Resource = [
          "${aws_s3_bucket.upload_bucket.arn}/${var.upload_prefix}*",
          "${aws_s3_bucket.upload_bucket.arn}/${var.processed_prefix}*",
          "${aws_s3_bucket.upload_bucket.arn}/${var.rejected_prefix}*",
          "${aws_s3_bucket.upload_bucket.arn}/${local.quicksight_data_prefix}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.upload_bucket.arn
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "${var.upload_prefix}*",
              "${var.processed_prefix}*",
              "${var.rejected_prefix}*",
              "${local.quicksight_data_prefix}/*"
            ]
          }
        }
      }
    ]
  })
}

# Lambda basic execution role attachment
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

# Lambda X-Ray tracing policy for Powertools
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
  role       = aws_iam_role.lambda_role.name
}

# Lambda EventBridge/S3 access policy
resource "aws_iam_role_policy" "lambda_eventbridge_policy" {
  name = "lambda_eventbridge_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/${var.upload_prefix}*"
      }
    ]
  })
}

# Lambda DynamoDB access policy
resource "aws_iam_role_policy" "lambda_dynamodb_policy" {
  name = "lambda_dynamodb_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.sales_data.arn,
          "${aws_dynamodb_table.sales_data.arn}/index/*"
        ]
      }
    ]
  })
}

# Lambda Bedrock access policy for AI analysis
resource "aws_iam_role_policy" "lambda_bedrock_policy" {
  name = "lambda_bedrock_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}"
        ]
      }
    ]
  })
}

# Step Function IAM role
resource "aws_iam_role" "step_function_role" {
  name = "upload_processor_step_function_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

# Step Function Lambda invocation policy
resource "aws_iam_role_policy" "step_function_policy" {
  name = "step_function_lambda_policy"
  role = aws_iam_role.step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.process_upload.arn,
          aws_lambda_function.calculate_metrics.arn,
          aws_lambda_function.write_metrics.arn,
          aws_lambda_function.check_all_stores.arn,
          aws_lambda_function.get_store_summaries.arn,
          aws_lambda_function.calc_company_metrics.arn,
          aws_lambda_function.calc_product_metrics.arn,
          aws_lambda_function.generate_report.arn,
          aws_lambda_function.detect_anomalies.arn,
          aws_lambda_function.analyze_trends.arn,
          aws_lambda_function.generate_recommendations.arn,
          aws_lambda_function.combine_insights.arn,
          aws_lambda_function.export_to_quicksight.arn
        ]
      }
    ]
  })
}

# Step Function SNS publish policy
resource "aws_iam_role_policy" "step_function_sns_policy" {
  name = "step_function_sns_policy"
  role = aws_iam_role.step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.sales_alerts.arn,
          aws_sns_topic.sales_daily_report.arn
        ]
      }
    ]
  })
}

# Step Function start execution policy (for triggering daily analysis)
resource "aws_iam_role_policy" "step_function_start_execution_policy" {
  name = "step_function_start_execution_policy"
  role = aws_iam_role.step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = [
          aws_sfn_state_machine.daily_analysis.arn
        ]
      }
    ]
  })
}

# EventBridge IAM role
resource "aws_iam_role" "eventbridge_step_function_role" {
  name = "eventbridge_step_function_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

# EventBridge Step Function execution policy
resource "aws_iam_role_policy" "eventbridge_step_function_policy" {
  name = "eventbridge_step_function_policy"
  role = aws_iam_role.eventbridge_step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = [
          aws_sfn_state_machine.upload_processor.arn
        ]
      }
    ]
  })
}

# EventBridge CloudWatch Logs policy
resource "aws_iam_role_policy" "eventbridge_logging" {
  name = "eventbridge_logging"
  role = aws_iam_role.eventbridge_step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.eventbridge_logs.arn}:*"
      }
    ]
  })
}

# Lambda policy for starting Step Functions (used by trigger_daily_analysis)
resource "aws_iam_role_policy" "lambda_step_functions_policy" {
  name = "lambda_step_functions_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution",
          "states:ListExecutions",
          "states:DescribeExecution"
        ]
        Resource = [
          aws_sfn_state_machine.daily_analysis.arn,
          "${aws_sfn_state_machine.daily_analysis.arn}:*"
        ]
      }
    ]
  })
}
