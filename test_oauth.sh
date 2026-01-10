#!/bin/bash
# Test OAuth endpoints for Brain MCP Server

BASE_URL="${1:-http://localhost:8084}"

echo "Testing Brain MCP Server OAuth Endpoints"
echo "Base URL: $BASE_URL"
echo ""

echo "=== Testing /.well-known/oauth-protected-resource ==="
curl -s "$BASE_URL/.well-known/oauth-protected-resource" | jq '.' || echo "Failed"
echo ""

echo "=== Testing /.well-known/oauth-authorization-server ==="
curl -s "$BASE_URL/.well-known/oauth-authorization-server" | jq '.' || echo "Failed"
echo ""

echo "=== Testing /.well-known/openid-configuration ==="
curl -s "$BASE_URL/.well-known/openid-configuration" | jq '.' || echo "Failed"
echo ""

echo "=== Testing /register (Dynamic Client Registration) ==="
curl -s -X POST "$BASE_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Client",
    "redirect_uris": ["http://localhost:3000/callback"]
  }' | jq '.' || echo "Failed"
echo ""

echo "=== Testing /authorize ==="
curl -s "$BASE_URL/authorize?client_id=test&redirect_uri=http://localhost/callback&response_type=code&state=xyz" | jq '.' || echo "Failed"
echo ""

echo "=== Testing /token ==="
curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=test_code&redirect_uri=http://localhost/callback" | jq '.' || echo "Failed"
echo ""

echo "All tests complete!"
