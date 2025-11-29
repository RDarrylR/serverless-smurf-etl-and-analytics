# Step Functions

# Step Functions state machine: Daily analysis workflow
resource "aws_sfn_state_machine" "daily_analysis" {
  name     = "daily-analysis"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/../backend/state-machines/daily-analysis.json", {
    get_store_summaries_lambda_arn      = aws_lambda_function.get_store_summaries.arn
    calc_company_metrics_lambda_arn     = aws_lambda_function.calc_company_metrics.arn
    calc_product_metrics_lambda_arn     = aws_lambda_function.calc_product_metrics.arn
    detect_anomalies_lambda_arn         = aws_lambda_function.detect_anomalies.arn
    analyze_trends_lambda_arn           = aws_lambda_function.analyze_trends.arn
    generate_recommendations_lambda_arn = aws_lambda_function.generate_recommendations.arn
    combine_insights_lambda_arn         = aws_lambda_function.combine_insights.arn
    generate_report_lambda_arn          = aws_lambda_function.generate_report.arn
    export_to_quicksight_lambda_arn     = aws_lambda_function.export_to_quicksight.arn
    sns_daily_report_topic_arn          = aws_sns_topic.sales_daily_report.arn
    sns_alerts_topic_arn                = aws_sns_topic.sales_alerts.arn
  })
}

# Step Functions state machine: Upload processor workflow
resource "aws_sfn_state_machine" "upload_processor" {
  name     = "upload-processor"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/../backend/state-machines/upload-processor.json", {
    process_upload_lambda_arn        = aws_lambda_function.process_upload.arn
    calculate_metrics_lambda_arn     = aws_lambda_function.calculate_metrics.arn
    write_metrics_lambda_arn         = aws_lambda_function.write_metrics.arn
    check_all_stores_lambda_arn      = aws_lambda_function.check_all_stores.arn
    sns_alerts_topic_arn             = aws_sns_topic.sales_alerts.arn
    daily_analysis_state_machine_arn = aws_sfn_state_machine.daily_analysis.arn
  })

  depends_on = [aws_sfn_state_machine.daily_analysis]
}
