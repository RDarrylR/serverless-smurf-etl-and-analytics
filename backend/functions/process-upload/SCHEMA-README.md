# JSON Schema Validation

This Lambda function validates uploaded JSON files against a defined schema before processing them into Parquet format.

## Schema Location

- **Schema file**: `upload-schema.json` (bundled with Lambda function)
- **Validation**: Performed in `process_upload.py` before Parquet conversion

## Schema Requirements

The uploaded JSON file must be:
- An **array** of objects (list of records)
- Contains at least **1 item**
- Each record must have these **required fields**:
  - `id` (string, minimum length 1)
  - `timestamp` (string, ISO 8601 date-time format)
  - `value` (number)

### Optional Fields

- `category` (string, one of: "A", "B", "C")
- `metadata` (object with optional `source` and `notes` fields)

### Additional Properties

**Not allowed** - only the fields defined in the schema are permitted.

## Valid Example

See `sample-valid.json`:
```json
[
  {
    "id": "rec-001",
    "timestamp": "2024-11-22T10:30:00Z",
    "value": 42.5,
    "category": "A",
    "metadata": {
      "source": "sensor-1",
      "notes": "Normal reading"
    }
  },
  {
    "id": "rec-002",
    "timestamp": "2024-11-22T10:31:00Z",
    "value": 38.2,
    "category": "B"
  }
]
```

## Invalid Example

See `sample-invalid.json` - This will be rejected because:
- First record: `timestamp` is not ISO 8601 format, `value` is string instead of number
- Second record: Missing required field `id`

## Processing Flow

### Valid Files
1. Upload → `uploads/` prefix
2. Validate against schema ✓
3. Convert to Parquet → `processed/` prefix

### Invalid Files
1. Upload → `uploads/` prefix
2. Validate against schema ✗
3. Copy to `rejected/` prefix
4. Create `{filename}.error.json` with validation details
5. No Parquet file created

## Rejected Files

When a file fails validation:
- **Original file** copied to: `rejected/{filename}.json`
- **Error details** saved to: `rejected/{filename}.json.error.json`
- **Metadata** attached with validation error message
- **CloudWatch logs** contain detailed error information

## Error Details Format

```json
{
  "original_file": "uploads/20241122_103000_data.json",
  "rejected_file": "rejected/20241122_103000_data.json",
  "error": "Validation failed: 'id' is a required property at path: 1",
  "timestamp": "2024-11-22 10:30:05"
}
```

## Modifying the Schema

To update the validation schema:

1. Edit `upload-schema.json` in this directory
2. Test with sample files
3. Redeploy Lambda function:
   ```bash
   cd infrastructure
   terraform apply
   ```

The schema is bundled with the Lambda deployment package and validated on every file upload.

## Testing Schema Validation

### Test with valid file:
```bash
# Upload sample-valid.json via frontend
# Check CloudWatch logs for: "Schema validation passed"
# Verify Parquet file appears in processed/ prefix
```

### Test with invalid file:
```bash
# Upload sample-invalid.json via frontend
# Check CloudWatch logs for: "Schema validation failed"
# Verify file appears in rejected/ prefix
# Verify error.json file is created
```

## CloudWatch Monitoring

Check Lambda logs at: `/aws/lambda/process_upload`

**Successful validation**:
```
Schema validation passed
Converted DataFrame to Parquet and saved to S3: s3://bucket/processed/file.parquet
```

**Failed validation**:
```
Schema validation failed: Validation failed: 'id' is a required property at path: 1
File rejected and moved to: rejected/20241122_103000_data.json
```
