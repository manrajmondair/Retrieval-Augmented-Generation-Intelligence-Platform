#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000}
API_KEY=${API_KEY:-changeme}

echo "Seeding sample documents..."
curl -s -H "x-api-key: $API_KEY" -F "files=@data/sample/policies.md" -F "files=@data/sample/faq.md" \
  "$API_URL/ingest" | jq . || true
echo "Done."

