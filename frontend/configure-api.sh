#!/bin/bash

# Script to configure frontend API URL from Terraform output
# Usage: ./configure-api.sh

set -e

echo "==========================================="
echo "Frontend API Configuration"
echo "==========================================="
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "Error: This script must be run from the frontend directory"
    exit 1
fi

# Check if Terraform is deployed
if [ ! -f "../infrastructure/terraform.tfstate" ]; then
    echo "Error: Terraform state not found. Please deploy infrastructure first:"
    echo "  cd ../infrastructure"
    echo "  terraform init"
    echo "  terraform apply"
    exit 1
fi

# Get API URL from Terraform output
echo "Fetching API Gateway URL from Terraform..."
cd ../infrastructure
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null)

if [ -z "$API_URL" ]; then
    echo "Error: Could not retrieve API Gateway URL from Terraform"
    echo "Make sure infrastructure is deployed with: terraform apply"
    exit 1
fi

cd ../frontend

echo "API Gateway URL: $API_URL"
echo ""

# Create or update .env file
if [ -f ".env" ]; then
    echo "Updating existing .env file..."
    # Remove old REACT_APP_API_URL line if it exists
    grep -v "^REACT_APP_API_URL=" .env > .env.tmp || true
    mv .env.tmp .env
else
    echo "Creating new .env file..."
fi

# Add the API URL
echo "REACT_APP_API_URL=$API_URL" >> .env

echo ""
echo "✓ Frontend configured successfully!"
echo ""
echo "API URL saved to: frontend/.env"
echo ""
echo "Next steps:"
echo "  1. Start the development server:"
echo "     npm start"
echo ""
echo "  2. Or build for production:"
echo "     npm run build"
echo ""
echo "==========================================="
