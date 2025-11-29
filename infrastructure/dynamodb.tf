# DynamoDB table for sales data aggregations
# Single table design for store summaries, product metrics, insights, and upload tracking

resource "aws_dynamodb_table" "sales_data" {
  name         = "SalesData"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # GSI for querying by date across all stores
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  tags = {
    Name        = "SalesData"
    Environment = "production"
    Project     = "serverless-file-upload-etl"
  }
}

# Output the table name and ARN for use by Lambda functions
output "dynamodb_table_name" {
  description = "Name of the DynamoDB sales data table"
  value       = aws_dynamodb_table.sales_data.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB sales data table"
  value       = aws_dynamodb_table.sales_data.arn
}
