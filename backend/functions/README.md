# Lambda Functions

This directory contains all Lambda function implementations for the serverless file upload ETL system.

## Structure

Each Lambda function has its own subdirectory with:
- Source code files
- `build.sh` - Build script for creating deployment package
- `README.md` - Function-specific documentation
- `requirements.txt` - Python dependencies (if needed)

```
functions/
├── generate-upload-url/        # Presigned URL generator
│   ├── lambda_function.py
│   ├── build.sh
│   └── README.md
└── process-upload/             # JSON to Parquet converter
    ├── process_upload.py
    ├── build.sh
    └── README.md
```

## Functions Overview

### generate-upload-url

**Purpose:** Generates presigned S3 URLs for secure file uploads

**Key Features:**
- Creates time-limited upload URLs (1 hour expiration)
- Adds timestamp to prevent filename collisions
- Handles CORS for browser uploads
- No external dependencies

**Triggers:** API Gateway (POST /generate-upload-url)

**See:** [generate-upload-url/README.md](generate-upload-url/README.md)

### process-upload

**Purpose:** Converts uploaded JSON files to Parquet format

**Key Features:**
- Automatic ETL processing on S3 upload
- Uses Pandas for data transformation
- Leverages AWS Data Wrangler for S3/Parquet operations
- 40-60% file size reduction

**Triggers:** EventBridge → Step Functions → Lambda

**See:** [process-upload/README.md](process-upload/README.md)

## Building Functions

### Build All Functions

From the `backend` directory:
```bash
./build-all.sh
```

This will:
1. Iterate through all function directories
2. Execute each `build.sh` script
3. Create deployment packages: `functions/*.zip`

### Build Individual Function

```bash
cd functions/generate-upload-url
./build.sh
```

Or:
```bash
cd functions/process-upload
./build.sh
```

## Deployment Packages

After building, deployment packages are created at:
- `functions/generate-upload-url.zip`
- `functions/process-upload.zip`

These zip files are referenced by Terraform in `infrastructure/main.tf`:
```terraform
filename = "${path.module}/../backend/functions/generate-upload-url.zip"
filename = "${path.module}/../backend/functions/process-upload.zip"
```

## Adding New Functions

To add a new Lambda function:

1. **Create directory:**
   ```bash
   mkdir -p functions/my-new-function
   cd functions/my-new-function
   ```

2. **Add source code:**
   ```bash
   # Create your Lambda handler
   touch lambda_handler.py
   ```

3. **Create build script:**
   ```bash
   cat > build.sh << 'EOF'
   #!/bin/bash
   cd "$(dirname "$0")"
   FUNCTION_NAME="my-new-function"
   echo "Building ${FUNCTION_NAME}..."
   BUILD_DIR="build"
   mkdir -p "$BUILD_DIR"
   cp *.py "$BUILD_DIR/"
   if [ -f "requirements.txt" ]; then
       pip install -r requirements.txt -t "$BUILD_DIR/"
   fi
   cd "$BUILD_DIR"
   zip -r "../${FUNCTION_NAME}.zip" .
   cd ..
   rm -rf "$BUILD_DIR"
   echo "✓ Lambda function packaged to functions/${FUNCTION_NAME}.zip"
   EOF
   chmod +x build.sh
   ```

4. **Create README:**
   Document your function's purpose, configuration, and usage

5. **Update Terraform:**
   Add the Lambda function resource in `infrastructure/main.tf`

6. **Build and deploy:**
   ```bash
   ./build.sh
   cd ../../infrastructure
   terraform apply
   ```

## Development Best Practices

### Function Organization
- Keep functions focused and single-purpose
- Use meaningful directory names (kebab-case)
- Include comprehensive README for each function

### Dependencies
- Use Lambda Layers for shared dependencies (pandas, numpy, etc.)
- Only bundle function-specific dependencies
- Keep deployment packages small (<50MB uncompressed)

### Testing
- Write unit tests for handler functions
- Test with sample events locally
- Use SAM CLI for local testing with Docker

### Error Handling
- Use structured logging with `print()` or `logging` module
- Include error context in exception messages
- Return proper status codes and error responses

### Environment Variables
- Define required env vars in function README
- Use Terraform to set env vars in `infrastructure/main.tf`
- Never hardcode secrets (use AWS Secrets Manager)

## CI/CD Integration

Example GitHub Actions workflow:
```yaml
name: Deploy Lambda Functions

on:
  push:
    branches: [main]
    paths:
      - 'backend/functions/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build Lambda Functions
        run: |
          cd backend
          ./build-all.sh

      - name: Deploy with Terraform
        run: |
          cd infrastructure
          terraform init
          terraform apply -auto-approve
```

## Monitoring

All Lambda functions automatically log to CloudWatch:
- `/aws/lambda/generate_upload_url`
- `/aws/lambda/process_upload`

View logs:
```bash
# Follow logs in real-time
aws logs tail /aws/lambda/generate_upload_url --follow

# View specific time range
aws logs tail /aws/lambda/process_upload --since 1h
```

## Troubleshooting

### Build fails
- Check Python version (3.12 required)
- Verify all source files are in function directory
- Check `build.sh` has execute permissions

### Function fails in AWS
- Check CloudWatch Logs for errors
- Verify IAM role has required permissions
- Check Lambda timeout settings
- Verify environment variables are set

### Large deployment package
- Use Lambda Layers for heavy dependencies
- Exclude test files and documentation from zip
- Consider using container images for very large functions

## Related Documentation

- [ARCHITECTURE.md](../../docs/ARCHITECTURE.md) - Overall system architecture
- [DEPLOYMENT.md](../../docs/DEPLOYMENT.md) - Deployment guide (SAM vs Terraform)
- [README.md](../../README.md) - Project overview and quick start
- Infrastructure: [infrastructure/](../../infrastructure/)
