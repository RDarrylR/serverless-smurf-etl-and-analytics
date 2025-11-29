output "api_gateway_url" {
  description = "API Gateway base URL"
  value       = aws_api_gateway_stage.api_stage.invoke_url
}

output "generate_upload_url_function_arn" {
  description = "Generate Upload URL Lambda Function ARN"
  value       = aws_lambda_function.upload_url_generator.arn
}

output "process_upload_function_arn" {
  description = "Process Upload Lambda Function ARN"
  value       = aws_lambda_function.process_upload.arn
}

output "state_machine_arn" {
  description = "Upload Processor Step Functions ARN"
  value       = aws_sfn_state_machine.upload_processor.arn
}

output "s3_bucket_name" {
  description = "S3 bucket for file uploads"
  value       = aws_s3_bucket.upload_bucket.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.upload_bucket.arn
} 