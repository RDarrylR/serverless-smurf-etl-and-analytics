#!/bin/bash
#
# Upload Sample Data Script
# Uploads all sample data files to the S3 bucket to trigger the ETL pipeline
#
# Usage: ./upload_sample_data.sh [--days N] [--delay N]
#   --days N     Upload only the first N days of data (default: all 30 days)
#   --delay N    Seconds to wait between days (default: 30, range: 0-300)
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SAMPLE_DATA_DIR="$PROJECT_DIR/sample_data"
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

S3_PREFIX="uploads"
NUM_STORES=11

# Defaults
DAYS_TO_UPLOAD=30
DELAY_BETWEEN_DAYS=30

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS_TO_UPLOAD="$2"
            shift 2
            ;;
        --delay)
            DELAY_BETWEEN_DAYS="$2"
            if [ "$DELAY_BETWEEN_DAYS" -lt 0 ] || [ "$DELAY_BETWEEN_DAYS" -gt 300 ]; then
                echo "Error: --delay must be between 0 and 300 seconds"
                exit 1
            fi
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--days N] [--delay N]"
            echo "  --days N     Upload only the first N days of data (default: 30)"
            echo "  --delay N    Seconds to wait between days (default: 30, range: 0-300)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if sample data exists
if [ ! -d "$SAMPLE_DATA_DIR" ]; then
    echo "Error: Sample data directory not found: $SAMPLE_DATA_DIR"
    echo "Run generate_sample_data.py first to create sample data."
    exit 1
fi

# Count files
TOTAL_FILES=$(ls "$SAMPLE_DATA_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
if [ "$TOTAL_FILES" -eq 0 ]; then
    echo "Error: No JSON files found in $SAMPLE_DATA_DIR"
    exit 1
fi

# Calculate date range (matches generate_sample_data.py: Oct 29 - Nov 27, 2025)
START_DATE="2025-10-29"
END_DATE=$(date -j -v+$((DAYS_TO_UPLOAD - 1))d -f "%Y-%m-%d" "$START_DATE" "+%Y-%m-%d" 2>/dev/null || \
           date -d "$START_DATE + $((DAYS_TO_UPLOAD - 1)) days" "+%Y-%m-%d")

FILES_TO_UPLOAD=$((DAYS_TO_UPLOAD * NUM_STORES))

echo "=============================================="
echo "Sample Data Upload Script"
echo "=============================================="
echo "Sample data directory: $SAMPLE_DATA_DIR"
echo "S3 bucket: s3://$S3_BUCKET/$S3_PREFIX/"
echo "Days to upload: $DAYS_TO_UPLOAD"
echo "Delay between days: ${DELAY_BETWEEN_DAYS}s"
echo "Files per day: $NUM_STORES"
echo "Total files to upload: $FILES_TO_UPLOAD"
echo "Date range: $START_DATE to $END_DATE"
echo "=============================================="
echo ""

# Confirm before uploading
read -p "Proceed with upload? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Upload cancelled."
    exit 0
fi

echo ""
echo "Starting upload..."
echo ""

START_TIME=$(date +%s)
TOTAL_UPLOADED=0

# Upload day by day
for day in $(seq 1 $DAYS_TO_UPLOAD); do
    DATE=$(date -j -v+$((day - 1))d -f "%Y-%m-%d" "$START_DATE" "+%Y-%m-%d" 2>/dev/null || \
           date -d "$START_DATE + $((day - 1)) days" "+%Y-%m-%d")

    echo "=== Day $day: $DATE ==="
    DAY_UPLOADED=0

    # Upload all stores for this day
    for store in $(seq 1 $NUM_STORES); do
        STORE_ID=$(printf "%04d" "$store")
        FILE="store_${STORE_ID}_${DATE}.json"
        FILEPATH="$SAMPLE_DATA_DIR/$FILE"

        if [ -f "$FILEPATH" ]; then
            if aws s3 cp "$FILEPATH" "s3://$S3_BUCKET/$S3_PREFIX/$FILE" --quiet; then
                echo "  [OK] $FILE"
                DAY_UPLOADED=$((DAY_UPLOADED + 1))
                TOTAL_UPLOADED=$((TOTAL_UPLOADED + 1))
            else
                echo "  [FAILED] $FILE"
            fi
        else
            echo "  [MISSING] $FILE"
        fi
    done

    echo "  Uploaded $DAY_UPLOADED files for $DATE"

    # Wait between days (except after the last day)
    if [ "$day" -lt "$DAYS_TO_UPLOAD" ] && [ "$DELAY_BETWEEN_DAYS" -gt 0 ]; then
        echo "  Waiting ${DELAY_BETWEEN_DAYS}s before next day..."
        sleep "$DELAY_BETWEEN_DAYS"
    fi
    echo ""
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "=============================================="
echo "Upload Complete"
echo "=============================================="
echo "Total files uploaded: $TOTAL_UPLOADED"
echo "Duration: ${DURATION}s"
echo ""
echo "The ETL pipeline will now process the files."
echo "Monitor progress in the AWS Step Functions console."
echo "=============================================="
