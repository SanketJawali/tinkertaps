#!/usr/bin/env bash

set -euo pipefail

PACKAGE_DIR="/tmp/tinkertaps-lambda"
ZIP_FILE="$HOME/programming/Tinkertaps/api/workers/tinkertaps-worker.zip"

rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

echo "Copying Lambda code..."
cp ./worker.py "$PACKAGE_DIR/"
cp -r ./scripts "$PACKAGE_DIR/"
cp -r ../app "$PACKAGE_DIR/"

echo "Installing dependencies..."
uv pip install \
    --target "$PACKAGE_DIR" \
    boto3 \
    sqlalchemy \
    asyncpg \
    pillow \
    pydantic \
    pydantic-settings

echo "Creating ZIP..."
rm -f "$ZIP_FILE"

(
    cd "$PACKAGE_DIR"
    zip -r "$ZIP_FILE" .
)

echo
echo "Lambda package created:"
echo "$ZIP_FILE"
echo
echo "Package contents:"
unzip -l "$ZIP_FILE" | head -30
