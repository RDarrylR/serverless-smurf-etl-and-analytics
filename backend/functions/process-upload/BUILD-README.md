# Build Process for process-upload Lambda

## Why a Build Step is Needed

This Lambda function uses the `jsonschema` library which has native dependencies (specifically `rpds-py` with compiled C extensions). These must be built for the **Linux arm64** platform that AWS Lambda uses with Graviton2, not your local development machine.

## Building the Lambda Package

**Before deploying with Terraform, you must run:**

```bash
cd backend/functions/process-upload
./build.sh
```

This script:
1. Creates a `package/` directory
2. Copies `process_upload.py` and `upload-schema.json`
3. Installs dependencies for **Linux arm64** platform (Graviton2)
4. Terraform will then create the deployment zip from `package/`

## Important Notes

### Platform-Specific Dependencies

The build script uses these pip flags to ensure Linux arm64 compatibility:
```bash
pip install -r requirements.txt -t package/ \
    --platform manylinux2014_aarch64 \
    --only-binary=:all: \
    --python-version 3.13
```

This downloads pre-compiled Linux ARM64 wheels instead of building from source on your Mac.

### When to Rebuild

You need to run `./build.sh` whenever you:
- Change `process_upload.py`
- Change `upload-schema.json`
- Update `requirements.txt`
- First time setting up the project

### Deployment Workflow

```bash
# 1. Make code changes
vim process_upload.py

# 2. Build for Linux
./build.sh

# 3. Deploy with Terraform
cd ../../../infrastructure
terraform apply
```

### Build Artifacts

The following directories/files are created and should NOT be committed to git:
- `package/` - Contains Lambda code and Linux dependencies
- `build/` - Temporary build directory (legacy)
- `*.zip` - Deployment archives

These are excluded via `.gitignore`.

## Troubleshooting

### "No module named 'rpds.rpds'" Error

This means the Lambda package has macOS dependencies instead of Linux ones.

**Solution**: Run `./build.sh` to rebuild with correct platform.

### pip Dependency Conflicts

You might see warnings about `attrs` version conflicts with `jsii`. This is expected and won't affect Lambda execution since jsii is only used for local Terraform development, not in the Lambda runtime.

### Missing package/ Directory Error from Terraform

```
Error: error archiving directory: could not archive missing directory: ./../backend/functions/process-upload/package
```

**Solution**: Run `./build.sh` to create the package directory.
