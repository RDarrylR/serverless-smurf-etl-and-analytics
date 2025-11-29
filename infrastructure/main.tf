# Main Terraform Configuration

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# AWS Provider configuration
provider "aws" {
  region = var.aws_region
}

# Generate random suffix for S3 bucket name
resource "random_string" "bucket_suffix" {
  length  = 7
  special = false
  upper   = false
}

# Local values
locals {
  # S3 bucket name with random suffix for global uniqueness
  s3_bucket_name = "${var.s3_bucket_name}-${random_string.bucket_suffix.result}"
}

# All resources have been organized into domain-specific files:
# - iam.tf            : IAM roles and policies
# - lambda.tf         : Lambda functions
# - api-gateway.tf    : API Gateway resources
# - s3.tf             : S3 bucket configuration
# - eventbridge.tf    : EventBridge rules and targets
# - step-functions.tf : Step Functions state machines
# - cloudwatch.tf     : CloudWatch log groups
# - dynamodb.tf       : DynamoDB tables
# - sns.tf            : SNS topics and subscriptions
# - quicksight.tf     : QuickSight resources (optional)
# - variables.tf      : Input variables
# - outputs.tf        : Output values
