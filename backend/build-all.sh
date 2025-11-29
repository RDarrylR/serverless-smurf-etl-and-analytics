#!/bin/bash

# Build Lambda functions that require pre-processing
# Most functions are zipped directly by Terraform's archive_file data source
# Only process-upload requires a build step (ARM64 dependencies)

set -e

# Ensure we're in the backend directory
cd "$(dirname "$0")"

echo "==========================================="
echo "Building Lambda functions..."
echo "==========================================="
echo ""

# Build process-upload (requires ARM64 pip dependencies)
echo "Building process-upload..."
(cd functions/process-upload && ./build.sh)
echo ""

echo "==========================================="
echo "✓ Build complete"
echo "==========================================="
echo ""
echo "Note: Other Lambda functions are zipped directly by Terraform."
echo "      Run 'terraform apply' to deploy all functions."
