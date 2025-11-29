# Frontend - Serverless File Upload ETL

React-based frontend for the serverless file upload ETL system.

## Overview

This frontend allows users to:
- Upload JSON files to S3 via presigned URLs
- View upload history
- Track upload status in real-time

## Prerequisites

- Node.js >= 16
- npm or yarn
- Backend infrastructure deployed (Terraform or SAM)

## Configuration

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure API Gateway URL

The frontend needs the API Gateway URL from your deployed backend infrastructure.

#### Option A: Automatic Configuration (Recommended)

Use the provided script to automatically fetch the API URL from Terraform:

```bash
# Make sure backend infrastructure is deployed first
cd ../infrastructure
terraform apply

# Return to frontend and run configuration script
cd ../frontend
./configure-api.sh
```

This creates a `.env` file with the correct API Gateway URL.

#### Option B: Manual Configuration

1. Get the API Gateway URL from Terraform:
   ```bash
   cd ../infrastructure
   terraform output api_gateway_url
   ```

2. Create `.env` file in the frontend directory:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set the API URL:
   ```bash
   REACT_APP_API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/generate-upload-url
   ```

#### Option C: Using SAM

If you deployed with SAM:

```bash
cd ../backend
sam deploy

# Get the API URL from SAM outputs
API_URL=$(sam list stack-outputs --stack-name file-upload-etl --output json | jq -r '.[] | select(.OutputKey=="ApiGatewayUrl") | .OutputValue')

# Create .env file
echo "REACT_APP_API_URL=$API_URL" > ../frontend/.env
```

### Configuration Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REACT_APP_API_URL` | API Gateway endpoint URL | Yes |

## Development

### Start Development Server

```bash
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view the app in your browser.

The page will reload when you make changes.

### Run Tests

```bash
npm test
```

Launches the test runner in interactive watch mode.

### Build for Production

```bash
npm run build
```

Builds the app for production to the `build` folder. The build is minified and optimized.

## Features

### File Upload

1. Click "Choose File" or drag-and-drop a JSON file
2. Only `.json` files are accepted
3. File is uploaded directly to S3 using a presigned URL
4. Upload progress is tracked in real-time

### Upload History

- View all uploaded files
- See upload timestamps
- Track S3 keys for uploaded files

## Architecture

```
User Browser
    ↓
React App (localhost:3000)
    ↓
API Gateway (presigned URL generation)
    ↓
Lambda Function (generates presigned URL)
    ↓
S3 Bucket (direct upload via presigned URL)
```

## CORS Configuration

The frontend communicates with:
- **API Gateway**: Configured in backend API spec
- **S3**: Configured in Terraform (infrastructure/s3.tf)

Default CORS origin: `http://localhost:3000`

For production deployment, update:
1. **Terraform variables** (`infrastructure/terraform.tfvars`):
   ```hcl
   frontend_origin = "https://yourdomain.com"
   ```

2. **Redeploy infrastructure**:
   ```bash
   cd ../infrastructure
   terraform apply
   ```

## Project Structure

```
frontend/
├── public/
│   ├── index.html
│   └── ...
├── src/
│   ├── App.js              # Main application component
│   ├── App.css             # Application styles
│   └── index.js            # React entry point
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── configure-api.sh        # API configuration script
├── package.json            # Dependencies
└── README.md               # This file
```

## Troubleshooting

### "Failed to get upload URL"

**Cause**: API Gateway URL not configured or incorrect

**Solution**:
1. Verify `.env` file exists with correct `REACT_APP_API_URL`
2. Check backend is deployed: `cd ../infrastructure && terraform output`
3. Restart development server after changing `.env`

### CORS Errors

**Cause**: S3 or API Gateway CORS not configured for frontend origin

**Solution**:
1. Check `frontend_origin` in Terraform variables matches your frontend URL
2. Ensure S3 CORS configuration includes your origin
3. Redeploy infrastructure: `cd ../infrastructure && terraform apply`

### "Upload to S3 failed"

**Cause**: Presigned URL expired or S3 permissions issue

**Solution**:
1. Presigned URLs expire after 1 hour - get a fresh URL
2. Verify Lambda has S3 write permissions (check Terraform IAM configuration)
3. Check CloudWatch Logs for Lambda errors:
   ```bash
   aws logs tail /aws/lambda/generate_upload_url --follow
   ```

### Environment Variables Not Loading

**Cause**: React environment variables must start with `REACT_APP_`

**Solution**:
1. Ensure variable is named `REACT_APP_API_URL` in `.env`
2. Restart development server after changing `.env`:
   ```bash
   # Stop the server (Ctrl+C) then:
   npm start
   ```

## Production Deployment

### Build Optimized Bundle

```bash
npm run build
```

### Deploy to S3 + CloudFront

```bash
# Build the app
npm run build

# Deploy to S3 (example)
aws s3 sync build/ s3://your-frontend-bucket/ --delete

# Invalidate CloudFront cache (if using CloudFront)
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Environment Variables for Production

Create a `.env.production` file:

```bash
REACT_APP_API_URL=https://your-production-api.execute-api.us-east-1.amazonaws.com/prod/generate-upload-url
```

Build will automatically use production environment variables.

## Related Documentation

- [Project README](../README.md)
- [Backend Documentation](../backend/README.md)
- [Infrastructure Documentation](../infrastructure/README.md)
- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)

## Technology Stack

- **React** - UI framework
- **Create React App** - Build tooling
- **Fetch API** - HTTP requests
- **AWS S3** - File storage (direct upload via presigned URLs)

## Learn More

- [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started)
- [React documentation](https://reactjs.org/)
- [AWS Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
