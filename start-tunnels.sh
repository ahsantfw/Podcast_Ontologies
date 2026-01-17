#!/bin/bash

echo "🌐 Starting Cloudflare Tunnels (Temporary Domains)"
echo "=================================================="
echo ""

# Check if services are running
check_service() {
    local port=$1
    local name=$2
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        echo "✅ $name is running on port $port"
        return 0
    else
        echo "❌ $name is NOT running on port $port"
        return 1
    fi
}

check_service 8000 "Backend"
check_service 3000 "Frontend"

echo ""
read -p "Continue anyway? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please start backend and frontend first, then run this script again."
    exit 1
fi

echo ""
echo "Starting tunnels..."
echo ""

# Start backend tunnel in background
echo "🔵 Starting Backend Tunnel..."
rm -f /tmp/backend-tunnel.log
cloudflared tunnel --url http://localhost:8000 > /tmp/backend-tunnel.log 2>&1 &
BACKEND_PID=$!
sleep 8

# Extract backend URL from log (try multiple patterns)
# The URL appears in a box format, so we need to extract it carefully
BACKEND_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' /tmp/backend-tunnel.log 2>/dev/null | head -1)

# If still not found, try looking for lines with "trycloudflare"
if [ -z "$BACKEND_URL" ]; then
    BACKEND_URL=$(grep 'trycloudflare' /tmp/backend-tunnel.log 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
fi

# Try extracting from the box format
if [ -z "$BACKEND_URL" ]; then
    BACKEND_URL=$(grep -A 2 'Your quick Tunnel' /tmp/backend-tunnel.log 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
fi

# If still not found, show log snippet
if [ -z "$BACKEND_URL" ]; then
    echo "⚠️  Could not extract backend URL automatically."
    echo "   Check the log output above for the URL, or run:"
    echo "   tail -f /tmp/backend-tunnel.log"
    echo ""
    echo "   Look for a line like:"
    echo "   +--------------------------------------------------------------------------------------------+"
    echo "   |  Your quick Tunnel has been created! Visit it at:                                          |"
    echo "   |  https://xxxx-xxxx.trycloudflare.com                                                       |"
    echo "   +--------------------------------------------------------------------------------------------+"
    echo ""
    BACKEND_URL=""
else
    echo "✅ Backend URL: $BACKEND_URL"
fi

# Start frontend tunnel in background
echo ""
echo "🟢 Starting Frontend Tunnel..."
rm -f /tmp/frontend-tunnel.log
cloudflared tunnel --url http://localhost:3000 > /tmp/frontend-tunnel.log 2>&1 &
FRONTEND_PID=$!
sleep 8

# Extract frontend URL from log
FRONTEND_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' /tmp/frontend-tunnel.log 2>/dev/null | head -1)

# If still not found, try looking for lines with "trycloudflare"
if [ -z "$FRONTEND_URL" ]; then
    FRONTEND_URL=$(grep 'trycloudflare' /tmp/frontend-tunnel.log 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
fi

# Try extracting from the box format
if [ -z "$FRONTEND_URL" ]; then
    FRONTEND_URL=$(grep -A 2 'Your quick Tunnel' /tmp/frontend-tunnel.log 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
fi

# If still not found, show instructions
if [ -z "$FRONTEND_URL" ]; then
    echo "⚠️  Could not extract frontend URL automatically."
    echo "   Check the log output above for the URL, or run:"
    echo "   tail -f /tmp/frontend-tunnel.log"
    echo ""
    FRONTEND_URL=""
else
    echo "✅ Frontend URL: $FRONTEND_URL"
fi

echo ""
echo "=========================================="
echo "✅ Tunnels Started!"
echo "=========================================="
echo ""

# Show URLs or instructions
if [ -n "$BACKEND_URL" ] && [ -n "$FRONTEND_URL" ]; then
    echo "📱 URLs:"
    echo "   Frontend: $FRONTEND_URL"
    echo "   Backend:  $BACKEND_URL"
    echo ""
    
    # Update frontend .env file
    ENV_FILE="frontend/.env"
    echo "📝 Updating frontend/.env file..."
    echo "VITE_API_URL=$BACKEND_URL/api/v1" > $ENV_FILE
    echo "✅ Frontend config updated!"
    echo "   Restart frontend dev server to apply changes"
else
    echo "📱 URLs will appear in the logs above."
    echo "   Look for lines with 'trycloudflare.com'"
    echo ""
    echo "   Or check logs directly:"
    echo "   Backend:  tail -f /tmp/backend-tunnel.log"
    echo "   Frontend: tail -f /tmp/frontend-tunnel.log"
    echo ""
    echo "   Once you have the backend URL, create frontend/.env:"
    echo "   VITE_API_URL=https://your-backend-url.trycloudflare.com/api/v1"
fi

echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f /tmp/backend-tunnel.log"
echo "   Frontend: tail -f /tmp/frontend-tunnel.log"
echo ""
echo "🛑 To stop tunnels:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   or: pkill cloudflared"
echo ""

# Keep script running
trap "echo ''; echo 'Stopping tunnels...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

