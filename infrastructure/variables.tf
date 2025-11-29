variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "s3_bucket_name" {
  description = "Base name for the S3 bucket (a random suffix will be appended for uniqueness)"
  type        = string

  validation {
    # Max 55 chars to leave room for 8-char random suffix (63 - 1 dash - 7 chars = 55)
    condition     = can(regex("^[a-z0-9][a-z0-9-]*[a-z0-9]$", var.s3_bucket_name)) && length(var.s3_bucket_name) >= 3 && length(var.s3_bucket_name) <= 55
    error_message = "S3 bucket name must be between 3-55 characters (to allow for random suffix), start/end with lowercase letter or number, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "upload_prefix" {
  description = "S3 prefix for uploaded files"
  type        = string
  default     = "uploads/"
}

variable "processed_prefix" {
  description = "S3 prefix for processed parquet files"
  type        = string
  default     = "processed/"
}

variable "rejected_prefix" {
  description = "S3 prefix for rejected files that failed validation"
  type        = string
  default     = "rejected/"
}

variable "frontend_origin" {
  description = "Frontend URL for CORS configuration"
  type        = string
  default     = "http://localhost:3000"
}

variable "expected_stores" {
  description = "Comma-separated list of expected store IDs"
  type        = string
  default     = "0001,0002,0003,0004,0005,0006,0007,0008,0009,0010,0011"
}

variable "alert_email" {
  description = "Email address for alerts and daily reports"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "Must be a valid email address."
  }
}

variable "alert_phone" {
  description = "Phone number for SMS alerts (E.164 format, e.g., +15551234567)"
  type        = string
  default     = ""
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for AI analysis (Amazon Nova Lite recommended)"
  type        = string
  default     = "amazon.nova-lite-v1:0"
}

variable "enable_quicksight" {
  description = "Enable QuickSight resources (requires QuickSight subscription)"
  type        = bool
  default     = false
}

variable "quicksight_user_arn" {
  description = "ARN of the QuickSight user/group to grant permissions (required if enable_quicksight is true)"
  type        = string
  default     = ""
}

variable "log_level" {
  description = "Log level for Lambda functions (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}

variable "daily_analysis_schedule" {
  description = "Cron expression for scheduled daily analysis. Runs only if analysis hasn't already completed for the day. Note: EventBridge cron uses UTC, so adjust for your timezone."
  type        = string
  default     = "cron(0 23 * * ? *)"  # 11 PM UTC - adjust for your timezone
}

variable "daily_analysis_timezone" {
  description = "Timezone for determining 'today' in daily analysis (e.g., America/New_York, Europe/London, Australia/Sydney)"
  type        = string
  default     = "America/New_York"
}

variable "enable_scheduled_analysis" {
  description = "Enable scheduled daily analysis even when not all stores have reported"
  type        = bool
  default     = true
}
