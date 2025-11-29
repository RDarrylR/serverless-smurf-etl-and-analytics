# QuickSight Resources for Sales Data Platform Dashboard
#
# Prerequisites:
# 1. QuickSight must be subscribed in the AWS account (Enterprise Edition recommended)
# 2. Run: aws quicksight create-account-subscription --aws-account-id <ACCOUNT_ID> \
#         --edition ENTERPRISE --authentication-method IAM_AND_QUICKSIGHT \
#         --account-name "SalesDataPlatform" --notification-email <EMAIL>
# 3. Create a QuickSight user (can be done via console or CLI)

locals {
  quicksight_namespace   = "default"
  quicksight_data_prefix = "quicksight"
}

# Data source for AWS account ID
data "aws_caller_identity" "current" {}

# IAM Role for QuickSight to access S3
resource "aws_iam_role" "quicksight_s3_role" {
  name = "quicksight-s3-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "quicksight.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "QuickSight S3 Access Role"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# IAM Policy for QuickSight S3 access
resource "aws_iam_role_policy" "quicksight_s3_policy" {
  name = "quicksight-s3-policy"
  role = aws_iam_role.quicksight_s3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:ListBucketVersions"
        ]
        Resource = [
          aws_s3_bucket.upload_bucket.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "${aws_s3_bucket.upload_bucket.arn}/${local.quicksight_data_prefix}/*"
        ]
      }
    ]
  })
}

# QuickSight Data Source - S3 for Store Summaries
resource "aws_quicksight_data_source" "store_summaries" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_source_id = "sales-store-summaries"
  name           = "Sales Store Summaries"
  type           = "S3"

  parameters {
    s3 {
      manifest_file_location {
        bucket = aws_s3_bucket.upload_bucket.id
        key    = "${local.quicksight_data_prefix}/store_summaries/manifest.json"
      }
      role_arn = aws_iam_role.quicksight_s3_role.arn
    }
  }

  permission {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:DeleteDataSource",
      "quicksight:UpdateDataSourcePermissions"
    ]
  }

  ssl_properties {
    disable_ssl = false
  }

  tags = {
    Name        = "Sales Store Summaries"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Data Source - S3 for Top Products
resource "aws_quicksight_data_source" "top_products" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_source_id = "sales-top-products"
  name           = "Sales Top Products"
  type           = "S3"

  parameters {
    s3 {
      manifest_file_location {
        bucket = aws_s3_bucket.upload_bucket.id
        key    = "${local.quicksight_data_prefix}/top_products/manifest.json"
      }
      role_arn = aws_iam_role.quicksight_s3_role.arn
    }
  }

  permission {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:DeleteDataSource",
      "quicksight:UpdateDataSourcePermissions"
    ]
  }

  ssl_properties {
    disable_ssl = false
  }

  tags = {
    Name        = "Sales Top Products"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Data Source - S3 for Anomalies
resource "aws_quicksight_data_source" "anomalies" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_source_id = "sales-anomalies"
  name           = "Sales Anomalies"
  type           = "S3"

  parameters {
    s3 {
      manifest_file_location {
        bucket = aws_s3_bucket.upload_bucket.id
        key    = "${local.quicksight_data_prefix}/anomalies/manifest.json"
      }
      role_arn = aws_iam_role.quicksight_s3_role.arn
    }
  }

  permission {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:DeleteDataSource",
      "quicksight:UpdateDataSourcePermissions"
    ]
  }

  ssl_properties {
    disable_ssl = false
  }

  tags = {
    Name        = "Sales Anomalies"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Data Source - S3 for Trends
resource "aws_quicksight_data_source" "trends" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_source_id = "sales-trends"
  name           = "Sales Trends"
  type           = "S3"

  parameters {
    s3 {
      manifest_file_location {
        bucket = aws_s3_bucket.upload_bucket.id
        key    = "${local.quicksight_data_prefix}/trends/manifest.json"
      }
      role_arn = aws_iam_role.quicksight_s3_role.arn
    }
  }

  permission {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:DeleteDataSource",
      "quicksight:UpdateDataSourcePermissions"
    ]
  }

  ssl_properties {
    disable_ssl = false
  }

  tags = {
    Name        = "Sales Trends"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Data Source - S3 for Recommendations
resource "aws_quicksight_data_source" "recommendations" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_source_id = "sales-recommendations"
  name           = "Sales Recommendations"
  type           = "S3"

  parameters {
    s3 {
      manifest_file_location {
        bucket = aws_s3_bucket.upload_bucket.id
        key    = "${local.quicksight_data_prefix}/recommendations/manifest.json"
      }
      role_arn = aws_iam_role.quicksight_s3_role.arn
    }
  }

  permission {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:DeleteDataSource",
      "quicksight:UpdateDataSourcePermissions"
    ]
  }

  ssl_properties {
    disable_ssl = false
  }

  tags = {
    Name        = "Sales Recommendations"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Dataset - Store Summaries
resource "aws_quicksight_data_set" "store_summaries" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = "sales-store-summaries-dataset"
  name           = "Sales Store Summaries Dataset"
  import_mode    = "SPICE"

  physical_table_map {
    physical_table_map_id = "store-summaries-table"

    s3_source {
      data_source_arn = aws_quicksight_data_source.store_summaries[0].arn

      input_columns {
        name = "date"
        type = "STRING"
      }
      input_columns {
        name = "store_id"
        type = "STRING"
      }
      input_columns {
        name = "year"
        type = "STRING"
      }
      input_columns {
        name = "month"
        type = "STRING"
      }
      input_columns {
        name = "day"
        type = "STRING"
      }
      input_columns {
        name = "total_sales"
        type = "STRING"
      }
      input_columns {
        name = "total_discount"
        type = "STRING"
      }
      input_columns {
        name = "net_sales"
        type = "STRING"
      }
      input_columns {
        name = "transaction_count"
        type = "STRING"
      }
      input_columns {
        name = "item_count"
        type = "STRING"
      }
      input_columns {
        name = "avg_transaction"
        type = "STRING"
      }
      input_columns {
        name = "record_count"
        type = "STRING"
      }
      input_columns {
        name = "created_at"
        type = "STRING"
      }
      input_columns {
        name = "payment_cash"
        type = "STRING"
      }
      input_columns {
        name = "payment_credit"
        type = "STRING"
      }
      input_columns {
        name = "payment_debit"
        type = "STRING"
      }
      input_columns {
        name = "payment_gift_card"
        type = "STRING"
      }

      upload_settings {
        format = "JSON"
      }
    }
  }

  logical_table_map {
    logical_table_map_id = "store-summaries-logical"
    alias                = "Store Summaries"

    source {
      physical_table_id = "store-summaries-table"
    }

    data_transforms {
      cast_column_type_operation {
        column_name     = "total_sales"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "total_discount"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "net_sales"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "transaction_count"
        new_column_type = "INTEGER"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "item_count"
        new_column_type = "INTEGER"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "avg_transaction"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "record_count"
        new_column_type = "INTEGER"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "payment_cash"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "payment_credit"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "payment_debit"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "payment_gift_card"
        new_column_type = "DECIMAL"
      }
    }
  }

  permissions {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSet",
      "quicksight:DescribeDataSetPermissions",
      "quicksight:PassDataSet",
      "quicksight:DescribeIngestion",
      "quicksight:ListIngestions",
      "quicksight:UpdateDataSet",
      "quicksight:DeleteDataSet",
      "quicksight:CreateIngestion",
      "quicksight:CancelIngestion",
      "quicksight:UpdateDataSetPermissions"
    ]
  }

  tags = {
    Name        = "Sales Store Summaries Dataset"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Dataset - Top Products
resource "aws_quicksight_data_set" "top_products" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = "sales-top-products-dataset"
  name           = "Sales Top Products Dataset"
  import_mode    = "SPICE"

  physical_table_map {
    physical_table_map_id = "top-products-table"

    s3_source {
      data_source_arn = aws_quicksight_data_source.top_products[0].arn

      input_columns {
        name = "date"
        type = "STRING"
      }
      input_columns {
        name = "store_id"
        type = "STRING"
      }
      input_columns {
        name = "sku"
        type = "STRING"
      }
      input_columns {
        name = "name"
        type = "STRING"
      }
      input_columns {
        name = "units_sold"
        type = "STRING"
      }
      input_columns {
        name = "revenue"
        type = "STRING"
      }

      upload_settings {
        format = "JSON"
      }
    }
  }

  logical_table_map {
    logical_table_map_id = "top-products-logical"
    alias                = "Top Products"

    source {
      physical_table_id = "top-products-table"
    }

    data_transforms {
      cast_column_type_operation {
        column_name     = "units_sold"
        new_column_type = "INTEGER"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "revenue"
        new_column_type = "DECIMAL"
      }
    }
  }

  permissions {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSet",
      "quicksight:DescribeDataSetPermissions",
      "quicksight:PassDataSet",
      "quicksight:DescribeIngestion",
      "quicksight:ListIngestions",
      "quicksight:UpdateDataSet",
      "quicksight:DeleteDataSet",
      "quicksight:CreateIngestion",
      "quicksight:CancelIngestion",
      "quicksight:UpdateDataSetPermissions"
    ]
  }

  tags = {
    Name        = "Sales Top Products Dataset"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Dataset - Anomalies
resource "aws_quicksight_data_set" "anomalies" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = "sales-anomalies-dataset"
  name           = "Sales Anomalies Dataset"
  import_mode    = "SPICE"

  physical_table_map {
    physical_table_map_id = "anomalies-table"

    s3_source {
      data_source_arn = aws_quicksight_data_source.anomalies[0].arn

      input_columns {
        name = "date"
        type = "STRING"
      }
      input_columns {
        name = "store_id"
        type = "STRING"
      }
      input_columns {
        name = "severity"
        type = "STRING"
      }
      input_columns {
        name = "title"
        type = "STRING"
      }
      input_columns {
        name = "description"
        type = "STRING"
      }
      input_columns {
        name = "metric_value"
        type = "STRING"
      }
      input_columns {
        name = "deviation_percent"
        type = "STRING"
      }

      upload_settings {
        format = "JSON"
      }
    }
  }

  logical_table_map {
    logical_table_map_id = "anomalies-logical"
    alias                = "Anomalies"

    source {
      physical_table_id = "anomalies-table"
    }

    data_transforms {
      cast_column_type_operation {
        column_name     = "metric_value"
        new_column_type = "DECIMAL"
      }
    }
    data_transforms {
      cast_column_type_operation {
        column_name     = "deviation_percent"
        new_column_type = "DECIMAL"
      }
    }
  }

  permissions {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSet",
      "quicksight:DescribeDataSetPermissions",
      "quicksight:PassDataSet",
      "quicksight:DescribeIngestion",
      "quicksight:ListIngestions",
      "quicksight:UpdateDataSet",
      "quicksight:DeleteDataSet",
      "quicksight:CreateIngestion",
      "quicksight:CancelIngestion",
      "quicksight:UpdateDataSetPermissions"
    ]
  }

  tags = {
    Name        = "Sales Anomalies Dataset"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Dataset - Trends
resource "aws_quicksight_data_set" "trends" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = "sales-trends-dataset"
  name           = "Sales Trends Dataset"
  import_mode    = "SPICE"

  physical_table_map {
    physical_table_map_id = "trends-table"

    s3_source {
      data_source_arn = aws_quicksight_data_source.trends[0].arn

      input_columns {
        name = "date"
        type = "STRING"
      }
      input_columns {
        name = "trend_type"
        type = "STRING"
      }
      input_columns {
        name = "significance"
        type = "STRING"
      }
      input_columns {
        name = "title"
        type = "STRING"
      }
      input_columns {
        name = "description"
        type = "STRING"
      }
      input_columns {
        name = "affected_items"
        type = "STRING"
      }

      upload_settings {
        format = "JSON"
      }
    }
  }

  logical_table_map {
    logical_table_map_id = "trends-logical"
    alias                = "Trends"

    source {
      physical_table_id = "trends-table"
    }
  }

  permissions {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSet",
      "quicksight:DescribeDataSetPermissions",
      "quicksight:PassDataSet",
      "quicksight:DescribeIngestion",
      "quicksight:ListIngestions",
      "quicksight:UpdateDataSet",
      "quicksight:DeleteDataSet",
      "quicksight:CreateIngestion",
      "quicksight:CancelIngestion",
      "quicksight:UpdateDataSetPermissions"
    ]
  }

  tags = {
    Name        = "Sales Trends Dataset"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Dataset - Recommendations
resource "aws_quicksight_data_set" "recommendations" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = "sales-recommendations-dataset"
  name           = "Sales Recommendations Dataset"
  import_mode    = "SPICE"

  physical_table_map {
    physical_table_map_id = "recommendations-table"

    s3_source {
      data_source_arn = aws_quicksight_data_source.recommendations[0].arn

      input_columns {
        name = "date"
        type = "STRING"
      }
      input_columns {
        name = "priority"
        type = "STRING"
      }
      input_columns {
        name = "category"
        type = "STRING"
      }
      input_columns {
        name = "title"
        type = "STRING"
      }
      input_columns {
        name = "description"
        type = "STRING"
      }
      input_columns {
        name = "affected_stores"
        type = "STRING"
      }
      input_columns {
        name = "affected_products"
        type = "STRING"
      }
      input_columns {
        name = "expected_impact"
        type = "STRING"
      }

      upload_settings {
        format = "JSON"
      }
    }
  }

  logical_table_map {
    logical_table_map_id = "recommendations-logical"
    alias                = "Recommendations"

    source {
      physical_table_id = "recommendations-table"
    }
  }

  permissions {
    principal = var.quicksight_user_arn
    actions = [
      "quicksight:DescribeDataSet",
      "quicksight:DescribeDataSetPermissions",
      "quicksight:PassDataSet",
      "quicksight:DescribeIngestion",
      "quicksight:ListIngestions",
      "quicksight:UpdateDataSet",
      "quicksight:DeleteDataSet",
      "quicksight:CreateIngestion",
      "quicksight:CancelIngestion",
      "quicksight:UpdateDataSetPermissions"
    ]
  }

  tags = {
    Name        = "Sales Recommendations Dataset"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# QuickSight Refresh Schedule for Store Summaries
resource "aws_quicksight_refresh_schedule" "store_summaries" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = aws_quicksight_data_set.store_summaries[0].data_set_id
  schedule_id    = "store-summaries-daily-refresh"

  schedule {
    refresh_type = "FULL_REFRESH"

    schedule_frequency {
      interval        = "DAILY"
      time_of_the_day = "06:00"
      timezone        = "UTC"
    }
  }
}

# QuickSight Refresh Schedule for Top Products
resource "aws_quicksight_refresh_schedule" "top_products" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = aws_quicksight_data_set.top_products[0].data_set_id
  schedule_id    = "top-products-daily-refresh"

  schedule {
    refresh_type = "FULL_REFRESH"

    schedule_frequency {
      interval        = "DAILY"
      time_of_the_day = "06:00"
      timezone        = "UTC"
    }
  }
}

# QuickSight Refresh Schedule for Anomalies
resource "aws_quicksight_refresh_schedule" "anomalies" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = aws_quicksight_data_set.anomalies[0].data_set_id
  schedule_id    = "anomalies-daily-refresh"

  schedule {
    refresh_type = "FULL_REFRESH"

    schedule_frequency {
      interval        = "DAILY"
      time_of_the_day = "06:00"
      timezone        = "UTC"
    }
  }
}

# QuickSight Refresh Schedule for Trends
resource "aws_quicksight_refresh_schedule" "trends" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = aws_quicksight_data_set.trends[0].data_set_id
  schedule_id    = "trends-daily-refresh"

  schedule {
    refresh_type = "FULL_REFRESH"

    schedule_frequency {
      interval        = "DAILY"
      time_of_the_day = "06:00"
      timezone        = "UTC"
    }
  }
}

# QuickSight Refresh Schedule for Recommendations
resource "aws_quicksight_refresh_schedule" "recommendations" {
  count = var.enable_quicksight ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = aws_quicksight_data_set.recommendations[0].data_set_id
  schedule_id    = "recommendations-daily-refresh"

  schedule {
    refresh_type = "FULL_REFRESH"

    schedule_frequency {
      interval        = "DAILY"
      time_of_the_day = "06:00"
      timezone        = "UTC"
    }
  }
}

# Outputs
output "quicksight_s3_role_arn" {
  description = "ARN of the IAM role for QuickSight S3 access"
  value       = aws_iam_role.quicksight_s3_role.arn
}

output "quicksight_data_sources" {
  description = "QuickSight data source IDs"
  value = var.enable_quicksight ? {
    store_summaries = aws_quicksight_data_source.store_summaries[0].data_source_id
    top_products    = aws_quicksight_data_source.top_products[0].data_source_id
    anomalies       = aws_quicksight_data_source.anomalies[0].data_source_id
    trends          = aws_quicksight_data_source.trends[0].data_source_id
    recommendations = aws_quicksight_data_source.recommendations[0].data_source_id
  } : {}
}

output "quicksight_datasets" {
  description = "QuickSight dataset IDs"
  value = var.enable_quicksight ? {
    store_summaries = aws_quicksight_data_set.store_summaries[0].data_set_id
    top_products    = aws_quicksight_data_set.top_products[0].data_set_id
    anomalies       = aws_quicksight_data_set.anomalies[0].data_set_id
    trends          = aws_quicksight_data_set.trends[0].data_set_id
    recommendations = aws_quicksight_data_set.recommendations[0].data_set_id
  } : {}
}
