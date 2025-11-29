#!/bin/bash

# Build script for process-upload Lambda function

# Ensure we're in the function directory
cd "$(dirname "$0")"

# Function name
FUNCTION_NAME="process-upload"

echo "Building ${FUNCTION_NAME}..."

# Create package directory (used by Terraform archive_file)
PACKAGE_DIR="package"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# Copy the Lambda function and schema
cp process_upload.py "$PACKAGE_DIR/"
cp upload-schema.json "$PACKAGE_DIR/"

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies for Linux/Lambda ARM64..."
    # Install for Linux ARM64 platform (Lambda runtime with Graviton)
    pip install -r requirements.txt -t "$PACKAGE_DIR/" \
        --platform manylinux2014_aarch64 \
        --only-binary=:all: \
        --python-version 3.13 \
        --implementation cp \
        --quiet
fi

echo "✓ Lambda function packaged to package/ directory"
echo "✓ Terraform will create deployment archive from package/"
echo "Note: This function uses AWS Lambda Layer for pandas/awswrangler"
