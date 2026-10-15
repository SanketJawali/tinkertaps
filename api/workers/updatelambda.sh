#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Updating Lambda function code..."
aws lambda update-function-code \
  --function-name tinkertaps-worker \
  --zip-file "fileb://${SCRIPT_DIR}/tinkertaps-worker.zip" \
  --endpoint-url "http://localhost:4566"

echo "Updating Lambda function configuration..."
aws lambda update-function-configuration \
  --function-name tinkertaps-worker \
  --environment "file://${SCRIPT_DIR}/env.json" \
  --endpoint-url "http://localhost:4566"

echo "Lambda update complete."
