# Lambda Functions

# AWS Lambda Powertools and Pandas layers for Python 3.13 ARM64
locals {
  powertools_layer_arn = "arn:aws:lambda:${var.aws_region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-arm64:27"
  pandas_layer_arn     = "arn:aws:lambda:${var.aws_region}:336392948345:layer:AWSSDKPandas-Python313-Arm64:5"

  # Common Powertools environment variables
  powertools_env_vars = {
    POWERTOOLS_SERVICE_NAME      = "sales-data-platform"
    POWERTOOLS_METRICS_NAMESPACE = "SalesDataPlatform"
    POWERTOOLS_LOG_LEVEL         = var.log_level
  }
}

# Archive Lambda function code: Generate presigned upload URLs
data "archive_file" "upload_url_generator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/generate-upload-url"
  output_path = "${path.module}/../backend/functions/generate-upload-url.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Generate presigned upload URLs
resource "aws_lambda_function" "upload_url_generator" {
  filename         = data.archive_file.upload_url_generator_zip.output_path
  function_name    = "generate_upload_url"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 1024
  source_code_hash = data.archive_file.upload_url_generator_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      S3_BUCKET     = aws_s3_bucket.upload_bucket.id
      UPLOAD_PREFIX = var.upload_prefix
    })
  }
}

# Archive Lambda function code: Process uploaded files
# Note: Run backend/functions/process-upload/build.sh before terraform apply to install dependencies
data "archive_file" "process_upload_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/process-upload/package"
  output_path = "${path.module}/../backend/functions/process-upload-deploy.zip"
  excludes    = ["__pycache__/", "*.pyc", "*.dist-info/"]
}

# Lambda function: Process uploaded files (JSON to Parquet)
resource "aws_lambda_function" "process_upload" {
  filename         = data.archive_file.process_upload_zip.output_path
  function_name    = "process_upload"
  role             = aws_iam_role.lambda_role.arn
  handler          = "process_upload.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.process_upload_zip.output_base64sha256

  layers = [local.powertools_layer_arn, local.pandas_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      S3_BUCKET        = aws_s3_bucket.upload_bucket.id
      PROCESSED_PREFIX = var.processed_prefix
      REJECTED_PREFIX  = var.rejected_prefix
    })
  }
}

# Archive Lambda function code: List files from S3
data "archive_file" "list_files_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/list-files"
  output_path = "${path.module}/../backend/functions/list-files.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: List files from S3
resource "aws_lambda_function" "list_files" {
  filename         = data.archive_file.list_files_zip.output_path
  function_name    = "list_files"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 1024
  source_code_hash = data.archive_file.list_files_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      S3_BUCKET        = aws_s3_bucket.upload_bucket.id
      PROCESSED_PREFIX = var.processed_prefix
      REJECTED_PREFIX  = var.rejected_prefix
      FRONTEND_ORIGIN  = var.frontend_origin
    })
  }
}

# Archive Lambda function code: Generate presigned download URLs
data "archive_file" "download_url_generator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/generate-download-url"
  output_path = "${path.module}/../backend/functions/generate-download-url.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Generate presigned download URLs
resource "aws_lambda_function" "download_url_generator" {
  filename         = data.archive_file.download_url_generator_zip.output_path
  function_name    = "generate_download_url"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 1024
  source_code_hash = data.archive_file.download_url_generator_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      S3_BUCKET = aws_s3_bucket.upload_bucket.id
    })
  }
}

# Archive Lambda function code: Calculate metrics from transaction data
data "archive_file" "calculate_metrics_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/calculate-metrics"
  output_path = "${path.module}/../backend/functions/calculate-metrics.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Calculate metrics from transaction data
resource "aws_lambda_function" "calculate_metrics" {
  filename         = data.archive_file.calculate_metrics_zip.output_path
  function_name    = "calculate_metrics"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.calculate_metrics_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      S3_BUCKET = aws_s3_bucket.upload_bucket.id
    })
  }
}

# Archive Lambda function code: Write metrics to DynamoDB
data "archive_file" "write_metrics_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/write-metrics"
  output_path = "${path.module}/../backend/functions/write-metrics.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Write metrics to DynamoDB
resource "aws_lambda_function" "write_metrics" {
  filename         = data.archive_file.write_metrics_zip.output_path
  function_name    = "write_metrics"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 1024
  source_code_hash = data.archive_file.write_metrics_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Check if all stores have uploaded
data "archive_file" "check_all_stores_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/check-all-stores"
  output_path = "${path.module}/../backend/functions/check-all-stores.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Check if all stores have uploaded
resource "aws_lambda_function" "check_all_stores" {
  filename         = data.archive_file.check_all_stores_zip.output_path
  function_name    = "check_all_stores"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 1024
  source_code_hash = data.archive_file.check_all_stores_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE  = aws_dynamodb_table.sales_data.name
      EXPECTED_STORES = var.expected_stores
    })
  }
}

# Archive Lambda function code: Get store summaries for daily analysis
data "archive_file" "get_store_summaries_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/get-store-summaries"
  output_path = "${path.module}/../backend/functions/get-store-summaries.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Get store summaries for daily analysis
resource "aws_lambda_function" "get_store_summaries" {
  filename         = data.archive_file.get_store_summaries_zip.output_path
  function_name    = "get_store_summaries"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.get_store_summaries_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Calculate company-wide metrics
data "archive_file" "calc_company_metrics_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/calc-company-metrics"
  output_path = "${path.module}/../backend/functions/calc-company-metrics.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Calculate company-wide metrics
resource "aws_lambda_function" "calc_company_metrics" {
  filename         = data.archive_file.calc_company_metrics_zip.output_path
  function_name    = "calc_company_metrics"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.calc_company_metrics_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Calculate product metrics across stores
data "archive_file" "calc_product_metrics_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/calc-product-metrics"
  output_path = "${path.module}/../backend/functions/calc-product-metrics.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Calculate product metrics across stores
resource "aws_lambda_function" "calc_product_metrics" {
  filename         = data.archive_file.calc_product_metrics_zip.output_path
  function_name    = "calc_product_metrics"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.calc_product_metrics_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Generate daily report
data "archive_file" "generate_report_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/generate-report"
  output_path = "${path.module}/../backend/functions/generate-report.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Generate daily report
resource "aws_lambda_function" "generate_report" {
  filename         = data.archive_file.generate_report_zip.output_path
  function_name    = "generate_report"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 1024
  source_code_hash = data.archive_file.generate_report_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = local.powertools_env_vars
  }
}

# Archive Lambda function code: Detect anomalies using Bedrock
data "archive_file" "detect_anomalies_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/detect-anomalies"
  output_path = "${path.module}/../backend/functions/detect-anomalies.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Detect anomalies using Bedrock
resource "aws_lambda_function" "detect_anomalies" {
  filename         = data.archive_file.detect_anomalies_zip.output_path
  function_name    = "detect_anomalies"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 60
  memory_size      = 1024
  source_code_hash = data.archive_file.detect_anomalies_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      DYNAMODB_TABLE   = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Analyze trends using Bedrock
data "archive_file" "analyze_trends_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/analyze-trends"
  output_path = "${path.module}/../backend/functions/analyze-trends.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Analyze trends using Bedrock
resource "aws_lambda_function" "analyze_trends" {
  filename         = data.archive_file.analyze_trends_zip.output_path
  function_name    = "analyze_trends"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 60
  memory_size      = 1024
  source_code_hash = data.archive_file.analyze_trends_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      DYNAMODB_TABLE   = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Generate recommendations using Bedrock
data "archive_file" "generate_recommendations_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/generate-recommendations"
  output_path = "${path.module}/../backend/functions/generate-recommendations.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Generate recommendations using Bedrock
resource "aws_lambda_function" "generate_recommendations" {
  filename         = data.archive_file.generate_recommendations_zip.output_path
  function_name    = "generate_recommendations"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 60
  memory_size      = 1024
  source_code_hash = data.archive_file.generate_recommendations_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      BEDROCK_MODEL_ID = var.bedrock_model_id
    })
  }
}

# Archive Lambda function code: Combine insights from Bedrock analysis
data "archive_file" "combine_insights_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/combine-insights"
  output_path = "${path.module}/../backend/functions/combine-insights.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Combine insights from Bedrock analysis
resource "aws_lambda_function" "combine_insights" {
  filename         = data.archive_file.combine_insights_zip.output_path
  function_name    = "combine_insights"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.combine_insights_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Export data to S3 for QuickSight
data "archive_file" "export_to_quicksight_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/export-to-quicksight"
  output_path = "${path.module}/../backend/functions/export-to-quicksight.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Export data to S3 for QuickSight
resource "aws_lambda_function" "export_to_quicksight" {
  filename         = data.archive_file.export_to_quicksight_zip.output_path
  function_name    = "export_to_quicksight"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 120
  memory_size      = 1024
  source_code_hash = data.archive_file.export_to_quicksight_zip.output_base64sha256

  layers = [local.powertools_layer_arn, local.pandas_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
      S3_BUCKET      = aws_s3_bucket.upload_bucket.id
    })
  }
}

# Archive Lambda function code: Get analytics data for frontend dashboard
data "archive_file" "get_analytics_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/get-analytics"
  output_path = "${path.module}/../backend/functions/get-analytics.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Get analytics data for frontend dashboard
resource "aws_lambda_function" "get_analytics" {
  filename         = data.archive_file.get_analytics_zip.output_path
  function_name    = "get_analytics"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.get_analytics_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
    })
  }
}

# Archive Lambda function code: Get historical trends for frontend dashboard
data "archive_file" "get_trends_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/functions/get-trends"
  output_path = "${path.module}/../backend/functions/get-trends.zip"
  excludes    = ["README.md", "build.sh", "requirements.txt", "build/", "__pycache__/", "*.pyc"]
}

# Lambda function: Get historical trends for frontend dashboard
resource "aws_lambda_function" "get_trends" {
  filename         = data.archive_file.get_trends_zip.output_path
  function_name    = "get_trends"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 1024
  source_code_hash = data.archive_file.get_trends_zip.output_base64sha256

  layers = [local.powertools_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = merge(local.powertools_env_vars, {
      DYNAMODB_TABLE = aws_dynamodb_table.sales_data.name
    })
  }
}
