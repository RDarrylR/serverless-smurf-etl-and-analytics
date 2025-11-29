"""
Generate Report Lambda

Generate a formatted daily sales report for SNS notification with AI insights.

Input: { "date": "...", "company_metrics": {...}, "product_metrics": [...], "insights": {...} }
Output: { "subject": "...", "message": "..." }
"""

import textwrap

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context: LambdaContext):
    date = event.get('date', 'Unknown')
    company_metrics = event.get('company_metrics', {})
    product_metrics = event.get('product_metrics', [])
    insights = event.get('insights', {})

    logger.info("Generating report", extra={
        "date": date,
        "has_company_metrics": company_metrics is not None,
        "product_count": len(product_metrics),
        "has_insights": insights is not None
    })

    report_message = format_report(date, company_metrics, product_metrics, insights)

    metrics.add_metric(name="ReportsGenerated", unit=MetricUnit.Count, value=1)
    metrics.add_dimension(name="Date", value=date)

    logger.info("Report generated", extra={"date": date})

    return {
        'date': date,
        'subject': f"Daily Sales Report - {date}",
        'message': report_message
    }


@tracer.capture_method
def format_report(date, company_metrics, product_metrics, insights):
    """Format the daily sales report as plain text."""
    lines = [
        "SMURF MEMORABILIA DAILY SALES REPORT",
        "=" * 40,
        f"Date: {date}",
        "",
        "COMPANY SUMMARY",
        "-" * 40,
        f"Total Sales: ${company_metrics.get('total_sales', 0):,.2f}",
        f"Transactions: {company_metrics.get('total_transactions', 0)}",
        f"Total Items: {company_metrics.get('total_items', 0)}",
        f"Stores Reporting: {company_metrics.get('store_count', 0)}/11",
        f"Avg Transaction: ${company_metrics.get('avg_transaction', 0):,.2f}",
        ""
    ]

    # Best/worst stores
    best = company_metrics.get('best_store', {})
    worst = company_metrics.get('worst_store', {})
    if best:
        lines.append(f"Best Store: #{best.get('store_id', 'N/A')} (${best.get('total_sales', 0):,.2f})")
    if worst:
        lines.append(f"Worst Store: #{worst.get('store_id', 'N/A')} (${worst.get('total_sales', 0):,.2f})")

    # Payment breakdown
    payments = company_metrics.get('payment_breakdown', {})
    if payments:
        lines.append("")
        lines.append("PAYMENT BREAKDOWN")
        lines.append("-" * 40)
        for method, amount in sorted(payments.items(), key=lambda x: -x[1]):
            lines.append(f"  {method.title()}: ${amount:,.2f}")

    # Top products
    if product_metrics:
        lines.append("")
        lines.append("TOP PRODUCTS")
        lines.append("-" * 40)
        for i, product in enumerate(product_metrics[:5], 1):
            lines.append(
                f"{i}. {product.get('name', 'Unknown')} - "
                f"{product.get('units_sold', 0)} units - "
                f"${product.get('revenue', 0):,.2f}"
            )

    # AI Insights section
    if insights:
        lines.append("")
        lines.append("AI INSIGHTS (Powered by Amazon Bedrock)")
        lines.append("=" * 40)

        # Anomalies
        anomalies = insights.get('anomalies', [])
        if anomalies:
            lines.append("")
            lines.append("ANOMALIES DETECTED")
            lines.append("-" * 40)
            for anomaly in anomalies[:5]:
                severity_icon = get_severity_icon(anomaly.get('severity', 'info'))
                lines.append(f"{severity_icon} {anomaly.get('title', 'Unknown anomaly')}")
                lines.extend(wrap_description(anomaly.get('description')))

        # Trends
        trends = insights.get('trends', [])
        if trends:
            lines.append("")
            lines.append("TRENDS IDENTIFIED")
            lines.append("-" * 40)
            for trend in trends[:5]:
                lines.append(f"-> {trend.get('title', 'Unknown trend')}")
                lines.extend(wrap_description(trend.get('description')))

        # Recommendations
        recommendations = insights.get('recommendations', [])
        if recommendations:
            lines.append("")
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 40)
            for i, rec in enumerate(recommendations[:5], 1):
                priority_icon = get_priority_icon(rec.get('priority', 'medium'))
                lines.append(f"{i}. {priority_icon} {rec.get('title', 'Unknown recommendation')}")
                lines.extend(wrap_description(rec.get('description')))

        if not anomalies and not trends and not recommendations:
            lines.append("")
            lines.append("No significant insights detected for today.")
    else:
        lines.append("")
        lines.append("(AI insights unavailable for this report)")

    lines.append("")
    lines.append("-" * 40)
    lines.append("Report generated by Sales Data Platform")

    return "\n".join(lines)


def get_severity_icon(severity: str) -> str:
    """Get icon for anomaly severity."""
    icons = {
        'critical': '[!!!]',
        'warning': '[!]',
        'info': '[i]'
    }
    return icons.get(severity, '[?]')


def get_priority_icon(priority: str) -> str:
    """Get icon for recommendation priority."""
    icons = {
        'high': '[HIGH]',
        'medium': '[MED]',
        'low': '[LOW]'
    }
    return icons.get(priority, '[?]')


def wrap_description(text: str, indent: str = "   ", width: int = 70) -> list:
    """Wrap long description text to multiple lines."""
    if not text:
        return []
    wrapped = textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)
    return [wrapped]
