#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000}
API_KEY=${API_KEY:-changeme}

cat > postman/RAG-Chatbot.postman_collection.json << EOF
{
  "info": {
    "name": "RAG Chatbot API",
    "description": "API collection for RAG Chatbot",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "$API_URL"
    },
    {
      "key": "api_key",
      "value": "$API_KEY"
    }
  ],
  "item": [
    {
      "name": "Health",
      "item": [
        {
          "name": "Health Check",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "x-api-key",
                "value": "{{api_key}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/healthz",
              "host": ["{{base_url}}"],
              "path": ["healthz"]
            }
          }
        },
        {
          "name": "Readiness Check",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "x-api-key",
                "value": "{{api_key}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/readyz",
              "host": ["{{base_url}}"],
              "path": ["readyz"]
            }
          }
        },
        {
          "name": "Config",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "x-api-key",
                "value": "{{api_key}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/config",
              "host": ["{{base_url}}"],
              "path": ["config"]
            }
          }
        }
      ]
    },
    {
      "name": "Ingest",
      "item": [
        {
          "name": "Ingest Documents",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "x-api-key",
                "value": "{{api_key}}"
              }
            ],
            "body": {
              "mode": "formdata",
              "formdata": [
                {
                  "key": "files",
                  "type": "file",
                  "src": []
                }
              ]
            },
            "url": {
              "raw": "{{base_url}}/ingest",
              "host": ["{{base_url}}"],
              "path": ["ingest"]
            }
          }
        }
      ]
    },
    {
      "name": "Query",
      "item": [
        {
          "name": "Query",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "x-api-key",
                "value": "{{api_key}}"
              },
              {
                "key": "content-type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"q\": \"What policies are covered?\",\n  \"top_k\": 12,\n  \"fusion\": \"rrf\"\n}"
            },
            "url": {
              "raw": "{{base_url}}/query",
              "host": ["{{base_url}}"],
              "path": ["query"]
            }
          }
        }
      ]
    },
    {
      "name": "Chat",
      "item": [
        {
          "name": "Chat Stream",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "x-api-key",
                "value": "{{api_key}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/chat/stream?q=What policies are covered?&top_k=12&fusion=rrf",
              "host": ["{{base_url}}"],
              "path": ["chat", "stream"],
              "query": [
                {
                  "key": "q",
                  "value": "What policies are covered?"
                },
                {
                  "key": "top_k",
                  "value": "12"
                },
                {
                  "key": "fusion",
                  "value": "rrf"
                }
              ]
            }
          }
        }
      ]
    }
  ]
}
EOF

echo "Postman collection exported to postman/RAG-Chatbot.postman_collection.json" 