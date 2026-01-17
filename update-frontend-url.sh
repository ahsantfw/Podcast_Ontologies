#!/bin/bash

echo "📝 Updating Frontend API URL from Tunnel Logs"
echo "=============================================="
echo ""

# Extract backend URL from log
BACKEND_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' /tmp/backend-tunnel.log 2>/dev/null | head -1)

if [ -z "$BACKEND_URL" ]; then
    echo "❌ Could not find backend URL in /tmp/backend-tunnel.log"
    echo ""
    echo "Please provide the backend tunnel URL:"
    read -p "Backend URL: " BACKEND_URL
fi

if [ -n "$BACKEND_URL" ]; then
    ENV_FILE="frontend/.env"
    echo "VITE_API_URL=$BACKEND_URL/api/v1" > $ENV_FILE
    echo "✅ Updated frontend/.env with:"
    echo "   VITE_API_URL=$BACKEND_URL/api/v1"
    echo ""
    echo "🔄 Restart frontend dev server to apply changes"
else
    echo "❌ No URL provided. Exiting."
    exit 1
fi
