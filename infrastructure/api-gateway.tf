# API Gateway

# REST API with OpenAPI specification
resource "aws_api_gateway_rest_api" "upload_api" {
  name = "sales-etl-api"
  body = templatefile("${path.module}/../backend/apis/sales-etl-api.yaml", {
    lambda_invoke_arn       = aws_lambda_function.upload_url_generator.invoke_arn
    list_files_invoke_arn   = aws_lambda_function.list_files.invoke_arn
    download_url_invoke_arn = aws_lambda_function.download_url_generator.invoke_arn
    analytics_invoke_arn    = aws_lambda_function.get_analytics.invoke_arn
    trends_invoke_arn       = aws_lambda_function.get_trends.invoke_arn
  })

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.upload_api.id

  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.upload_api.body))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "api_stage" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.upload_api.id
  stage_name    = "prod"
}

# Lambda permission for API Gateway invocation (upload URL generator)
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_url_generator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.upload_api.execution_arn}/*/*"
}

# Lambda permission for API Gateway invocation (list files)
resource "aws_lambda_permission" "apigw_list_files" {
  statement_id  = "AllowAPIGatewayInvokeListFiles"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_files.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.upload_api.execution_arn}/*/*"
}

# Lambda permission for API Gateway invocation (download URL generator)
resource "aws_lambda_permission" "apigw_download_url" {
  statement_id  = "AllowAPIGatewayInvokeDownloadUrl"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.download_url_generator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.upload_api.execution_arn}/*/*"
}

# Lambda permission for API Gateway invocation (get analytics)
resource "aws_lambda_permission" "apigw_get_analytics" {
  statement_id  = "AllowAPIGatewayInvokeGetAnalytics"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_analytics.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.upload_api.execution_arn}/*/*"
}

# Lambda permission for API Gateway invocation (get trends)
resource "aws_lambda_permission" "apigw_get_trends" {
  statement_id  = "AllowAPIGatewayInvokeGetTrends"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_trends.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.upload_api.execution_arn}/*/*"
}
