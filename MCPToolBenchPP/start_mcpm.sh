#!/bin/bash
# Start mcpm with a fresh PayPal access token
# Usage: ./start_mcpm.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_CONFIG="$SCRIPT_DIR/.venv/lib/python3.12/site-packages/mcp_marketplace/app/mcp_tool_use/data/mcp/config/mcp_config.json"
MCPM="$SCRIPT_DIR/.venv/bin/mcpm"

PAYPAL_CLIENT_ID="AXlzUCD9lqdTeUISUre2N03U9fCSALxP7qsmrqPChYoIAVmQWhkCYCp4iLUwwjVfUotrcPXYgwS311DQ"
PAYPAL_SECRET="EAeczFS8lcPa5NkNylskF1O1i26UxJsABnobHuuEHkl9Uy_y2M00KeSA00dD82dtewWawad8joc_cU7R"

# 1. Kill existing mcpm
echo "[1/4] Stopping existing mcpm..."
kill -9 $(lsof -ti:5000) 2>/dev/null || true
sleep 2

# 2. Get fresh PayPal access token
echo "[2/4] Fetching fresh PayPal sandbox access token..."
TOKEN_RESPONSE=$(curl -s -X POST https://api-m.sandbox.paypal.com/v1/oauth2/token \
  -u "$PAYPAL_CLIENT_ID:$PAYPAL_SECRET" \
  -d "grant_type=client_credentials")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "ERROR: Failed to get PayPal access token"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "   Got token: ${ACCESS_TOKEN:0:20}..."

# 3. Update mcp_config.json with new token
echo "[3/4] Updating mcp_config.json..."
python3 -c "
import json
with open('$MCP_CONFIG', 'r') as f:
    config = json.load(f)
config['mcpServers']['paypal']['env']['PAYPAL_ACCESS_TOKEN'] = '$ACCESS_TOKEN'
with open('$MCP_CONFIG', 'w') as f:
    json.dump(config, f, indent=2)
print('   Config updated.')
"

# 4. Start mcpm
echo "[4/4] Starting mcpm..."
nohup "$MCPM" run > /tmp/mcpm.log 2>&1 &
echo "   mcpm started (PID: $!)"
echo "   Log: /tmp/mcpm.log"
echo "   Waiting ~45s for servers to initialize..."
sleep 45
echo ""
echo "Done! All MCP servers should be ready."
echo "Verify: curl -s http://127.0.0.1:5000/api/query -X POST -H 'Content-Type: application/json' -d '{\"server_id\":\"paypal\",\"tool_name\":\"create_invoice\",\"tool_input\":{\"detail\":{\"currency_code\":\"USD\"},\"invoicer\":{\"business_name\":\"Test\"},\"items\":[{\"name\":\"Test\",\"quantity\":\"1\",\"unit_amount\":{\"value\":\"1.00\",\"currency_code\":\"USD\"}}]}}'"
