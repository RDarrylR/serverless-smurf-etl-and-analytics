#!/bin/bash

# QuickSight Restore Script
# Restores analyses and dashboards from exported JSON definitions
#
# Prerequisites:
# 1. Terraform stack must be deployed (creates data sources and datasets)
# 2. Export files must exist in ./exports/
#
# Usage:
#   ./restore-quicksight.sh [dashboard|analyses|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORTS_DIR="$SCRIPT_DIR/exports"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-us-east-1}"

echo "=============================================="
echo "QuickSight Restore Script"
echo "=============================================="
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Exports Dir: $EXPORTS_DIR"
echo ""

# Check if exports exist
if [ ! -d "$EXPORTS_DIR" ]; then
    echo "Error: Exports directory not found at $EXPORTS_DIR"
    echo "Run the export script first or ensure exports exist."
    exit 1
fi

restore_dashboard() {
    local json_file="$1"
    local dashboard_id=$(jq -r '.DashboardId' "$json_file")
    local dashboard_name=$(jq -r '.Name' "$json_file")

    echo "Restoring dashboard: $dashboard_name ($dashboard_id)"

    # Extract just the Definition part
    local definition=$(jq '.Definition' "$json_file")

    # Check if dashboard already exists
    if aws quicksight describe-dashboard --aws-account-id "$ACCOUNT_ID" --dashboard-id "$dashboard_id" &>/dev/null; then
        echo "  Dashboard exists, updating..."
        aws quicksight update-dashboard \
            --aws-account-id "$ACCOUNT_ID" \
            --dashboard-id "$dashboard_id" \
            --name "$dashboard_name" \
            --definition "$definition" \
            --region "$REGION"
    else
        echo "  Creating new dashboard..."
        aws quicksight create-dashboard \
            --aws-account-id "$ACCOUNT_ID" \
            --dashboard-id "$dashboard_id" \
            --name "$dashboard_name" \
            --definition "$definition" \
            --region "$REGION"
    fi

    echo "  Done: $dashboard_name"
}

restore_analysis() {
    local json_file="$1"
    local analysis_id=$(jq -r '.AnalysisId' "$json_file")
    local analysis_name=$(jq -r '.Name' "$json_file")

    echo "Restoring analysis: $analysis_name ($analysis_id)"

    # Extract just the Definition part
    local definition=$(jq '.Definition' "$json_file")

    # Check if analysis already exists
    if aws quicksight describe-analysis --aws-account-id "$ACCOUNT_ID" --analysis-id "$analysis_id" &>/dev/null; then
        echo "  Analysis exists, updating..."
        aws quicksight update-analysis \
            --aws-account-id "$ACCOUNT_ID" \
            --analysis-id "$analysis_id" \
            --name "$analysis_name" \
            --definition "$definition" \
            --region "$REGION"
    else
        echo "  Creating new analysis..."
        aws quicksight create-analysis \
            --aws-account-id "$ACCOUNT_ID" \
            --analysis-id "$analysis_id" \
            --name "$analysis_name" \
            --definition "$definition" \
            --region "$REGION"
    fi

    echo "  Done: $analysis_name"
}

case "${1:-all}" in
    dashboard)
        echo "Restoring dashboard only..."
        for f in "$EXPORTS_DIR"/dashboard-*.json; do
            [ -f "$f" ] && restore_dashboard "$f"
        done
        ;;
    analyses)
        echo "Restoring analyses only..."
        for f in "$EXPORTS_DIR"/analysis-*.json; do
            [ -f "$f" ] && restore_analysis "$f"
        done
        ;;
    all)
        echo "Restoring all analyses and dashboards..."
        echo ""
        echo "--- Analyses ---"
        for f in "$EXPORTS_DIR"/analysis-*.json; do
            [ -f "$f" ] && restore_analysis "$f"
        done
        echo ""
        echo "--- Dashboards ---"
        for f in "$EXPORTS_DIR"/dashboard-*.json; do
            [ -f "$f" ] && restore_dashboard "$f"
        done
        ;;
    *)
        echo "Usage: $0 [dashboard|analyses|all]"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "Restore complete!"
echo "=============================================="
echo ""
echo "Access your dashboard at:"
echo "  https://$REGION.quicksight.aws.amazon.com/"
