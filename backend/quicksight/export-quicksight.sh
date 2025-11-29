#!/bin/bash

# QuickSight Export Script
# Exports all analyses and dashboards to JSON files for backup/restore
#
# Usage:
#   ./export-quicksight.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORTS_DIR="$SCRIPT_DIR/exports"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-us-east-1}"

echo "=============================================="
echo "QuickSight Export Script"
echo "=============================================="
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Exports Dir: $EXPORTS_DIR"
echo ""

# Create exports directory
mkdir -p "$EXPORTS_DIR"

# Export dashboards
echo "--- Exporting Dashboards ---"
dashboard_ids=$(aws quicksight list-dashboards --aws-account-id "$ACCOUNT_ID" --query 'DashboardSummaryList[].DashboardId' --output text 2>/dev/null || echo "")

if [ -z "$dashboard_ids" ]; then
    echo "No dashboards found"
else
    for dashboard_id in $dashboard_ids; do
        dashboard_name=$(aws quicksight describe-dashboard --aws-account-id "$ACCOUNT_ID" --dashboard-id "$dashboard_id" --query 'Dashboard.Name' --output text 2>/dev/null)
        # Create safe filename
        safe_name=$(echo "$dashboard_name" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-')
        output_file="$EXPORTS_DIR/dashboard-$safe_name.json"

        echo "Exporting: $dashboard_name -> $output_file"
        aws quicksight describe-dashboard-definition \
            --aws-account-id "$ACCOUNT_ID" \
            --dashboard-id "$dashboard_id" \
            --region "$REGION" \
            > "$output_file"
    done
fi

# Export analyses
echo ""
echo "--- Exporting Analyses ---"
analysis_ids=$(aws quicksight list-analyses --aws-account-id "$ACCOUNT_ID" --query 'AnalysisSummaryList[].AnalysisId' --output text 2>/dev/null || echo "")

if [ -z "$analysis_ids" ]; then
    echo "No analyses found"
else
    for analysis_id in $analysis_ids; do
        analysis_name=$(aws quicksight describe-analysis --aws-account-id "$ACCOUNT_ID" --analysis-id "$analysis_id" --query 'Analysis.Name' --output text 2>/dev/null)
        # Create safe filename using ID (names might not be unique)
        output_file="$EXPORTS_DIR/analysis-$analysis_id.json"

        echo "Exporting: $analysis_name -> $output_file"
        aws quicksight describe-analysis-definition \
            --aws-account-id "$ACCOUNT_ID" \
            --analysis-id "$analysis_id" \
            --region "$REGION" \
            > "$output_file"
    done
fi

echo ""
echo "=============================================="
echo "Export complete!"
echo "=============================================="
echo ""
echo "Exported files:"
ls -la "$EXPORTS_DIR"
echo ""
echo "To restore after recreating infrastructure:"
echo "  ./restore-quicksight.sh all"
