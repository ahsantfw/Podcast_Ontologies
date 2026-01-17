#!/bin/bash

echo "🌐 Cloudflare Tunnel Setup Script"
echo "=================================="
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed"
    echo "Install it with: sudo apt install cloudflared"
    exit 1
fi

echo "✅ cloudflared is installed"
echo ""

# Step 1: Login
echo "Step 1: Login to Cloudflare"
echo "This will open a browser window..."
read -p "Press Enter to continue..."
cloudflared tunnel login

# Step 2: Create tunnel
echo ""
echo "Step 2: Creating tunnel..."
TUNNEL_NAME="kg-tunnel"
cloudflared tunnel create $TUNNEL_NAME

# Get tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}')
echo "✅ Tunnel created: $TUNNEL_ID"

# Step 3: Create DNS records
echo ""
echo "Step 3: Creating DNS records..."
read -p "Enter your domain (e.g., example.com): " DOMAIN
read -p "Enter subdomain for frontend (e.g., app): " FRONTEND_SUBDOMAIN
read -p "Enter subdomain for API (e.g., api): " API_SUBDOMAIN

FRONTEND_HOST="${FRONTEND_SUBDOMAIN}.${DOMAIN}"
API_HOST="${API_SUBDOMAIN}.${DOMAIN}"

cloudflared tunnel route dns $TUNNEL_NAME $FRONTEND_HOST
cloudflared tunnel route dns $TUNNEL_NAME $API_HOST

echo "✅ DNS records created"

# Step 4: Update config file
echo ""
echo "Step 4: Updating configuration..."
CONFIG_FILE="cloudflare-tunnel.yml"
sed -i "s/your-tunnel-id/$TUNNEL_ID/g" $CONFIG_FILE
sed -i "s/your-app.your-domain.com/$FRONTEND_HOST/g" $CONFIG_FILE
sed -i "s/api.your-app.your-domain.com/$API_HOST/g" $CONFIG_FILE

echo "✅ Configuration updated"
echo ""
echo "📝 Next steps:"
echo "1. Make sure backend is running: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "2. Make sure frontend is running: cd frontend && npm run dev"
echo "3. Start tunnel: cloudflared tunnel --config $CONFIG_FILE run $TUNNEL_NAME"
echo ""
echo "🌐 Your app will be available at:"
echo "   Frontend: https://$FRONTEND_HOST"
echo "   Backend:  https://$API_HOST"
