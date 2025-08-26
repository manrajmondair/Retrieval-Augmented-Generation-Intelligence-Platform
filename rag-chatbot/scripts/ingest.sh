#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000}
API_KEY=${API_KEY:-changeme}

if [ $# -eq 0 ]; then
    echo "Usage: $0 <file1> [file2] [file3] ..."
    echo "Example: $0 data/sample/policies.md data/sample/faq.md"
    exit 1
fi

echo "Ingesting documents..."
curl -s -H "x-api-key: $API_KEY" \
  -F "files=@$1" \
  "$API_URL/ingest" | jq . || true

echo "Done." 