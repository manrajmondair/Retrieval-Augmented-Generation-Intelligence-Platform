#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000}
API_KEY=${API_KEY:-changeme}

echo "Running RAG Chatbot benchmark..."

# Test health
echo "Testing health endpoint..."
curl -s -H "x-api-key: $API_KEY" "$API_URL/healthz" | jq .

# Test readiness
echo "Testing readiness endpoint..."
curl -s -H "x-api-key: $API_KEY" "$API_URL/readyz" | jq .

# Test config
echo "Testing config endpoint..."
curl -s -H "x-api-key: $API_KEY" "$API_URL/config" | jq .

# Test query (if system is ready)
echo "Testing query endpoint..."
curl -s -H "x-api-key: $API_KEY" \
  -X POST "$API_URL/query" \
  -H "content-type: application/json" \
  -d '{"q":"What policies are covered?"}' | jq . || echo "Query failed - system may not be ready"

echo "Benchmark complete." 