#!/bin/bash

# Clear all data for a specific date from S3 and DynamoDB
# Usage: ./clear-day-data.sh [DATE]
# Example: ./clear-day-data.sh 2025-01-15

set -e

# Default date if not provided
DATE=${1:-"2025-01-15"}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$PROJECT_DIR/infrastructure"

# Get S3 bucket from terraform output or environment variable
if [ -n "$S3_BUCKET" ]; then
    : # Use environment variable if set
elif [ -d "$INFRA_DIR/.terraform" ]; then
    S3_BUCKET=$(cd "$INFRA_DIR" && terraform output -raw s3_bucket_name 2>/dev/null) || true
fi

if [ -z "$S3_BUCKET" ]; then
    echo "Error: S3_BUCKET not set. Either:"
    echo "  1. Set S3_BUCKET environment variable: export S3_BUCKET=your-bucket-name"
    echo "  2. Ensure terraform has been applied in infrastructure/"
    exit 1
fi

DYNAMODB_TABLE="SalesData"
REGION="us-east-1"

echo "=== Clearing all data for date: $DATE ==="
echo ""

# Parse date components for S3 paths
YEAR=$(echo "$DATE" | cut -d'-' -f1)
MONTH=$(echo "$DATE" | cut -d'-' -f2)
DAY=$(echo "$DATE" | cut -d'-' -f3)

# 1. Clear S3 uploads for this date
echo "Clearing S3 uploads..."
aws s3 rm "s3://${S3_BUCKET}/uploads/" --recursive --exclude "*" --include "store_*_${DATE}.json" 2>/dev/null || true

# 2. Clear S3 processed parquet files for this date
echo "Clearing S3 processed files..."
aws s3 rm "s3://${S3_BUCKET}/processed/year=${YEAR}/month=${MONTH}/day=${DAY}/" --recursive 2>/dev/null || true

# 3. Clear S3 rejected files for this date
echo "Clearing S3 rejected files..."
aws s3 rm "s3://${S3_BUCKET}/rejected/" --recursive --exclude "*" --include "store_*_${DATE}*" 2>/dev/null || true

# 4. Clear DynamoDB records for this date
echo "Clearing DynamoDB records..."

# Query for all records with PK starting with DATE#
# This includes: UPLOAD#STORE#, SUMMARY#COMPANY, PRODUCT#, INSIGHT#
echo "  Querying DATE#${DATE} records..."
ITEMS=$(aws dynamodb query \
    --table-name "$DYNAMODB_TABLE" \
    --key-condition-expression "PK = :pk" \
    --expression-attribute-values "{\":pk\":{\"S\":\"DATE#${DATE}\"}}" \
    --projection-expression "PK, SK" \
    --region "$REGION" \
    --output json 2>/dev/null | jq -c '.Items[]' 2>/dev/null)

if [ -n "$ITEMS" ]; then
    echo "$ITEMS" | while read -r item; do
        PK=$(echo "$item" | jq -r '.PK.S')
        SK=$(echo "$item" | jq -r '.SK.S')
        echo "  Deleting: PK=$PK, SK=$SK"
        aws dynamodb delete-item \
            --table-name "$DYNAMODB_TABLE" \
            --key "{\"PK\":{\"S\":\"$PK\"},\"SK\":{\"S\":\"$SK\"}}" \
            --region "$REGION" 2>/dev/null
    done
fi

# Query for store daily summaries (PK=STORE#XXXX, SK=DATE#yyyy-mm-dd)
echo "  Querying store summary records..."
for STORE_ID in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010 0011; do
    RESULT=$(aws dynamodb get-item \
        --table-name "$DYNAMODB_TABLE" \
        --key "{\"PK\":{\"S\":\"STORE#${STORE_ID}\"},\"SK\":{\"S\":\"DATE#${DATE}\"}}" \
        --projection-expression "PK, SK" \
        --region "$REGION" \
        --output json 2>/dev/null)

    if echo "$RESULT" | jq -e '.Item' >/dev/null 2>&1; then
        echo "  Deleting: PK=STORE#${STORE_ID}, SK=DATE#${DATE}"
        aws dynamodb delete-item \
            --table-name "$DYNAMODB_TABLE" \
            --key "{\"PK\":{\"S\":\"STORE#${STORE_ID}\"},\"SK\":{\"S\":\"DATE#${DATE}\"}}" \
            --region "$REGION" 2>/dev/null
    fi
done

echo ""
echo "=== Data cleared for $DATE ==="
echo ""
echo "You can now re-upload data for this date:"
echo "  ./scripts/upload-all-stores.sh $DATE"
