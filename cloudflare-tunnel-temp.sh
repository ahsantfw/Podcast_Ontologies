#!/bin/bash

echo "🌐 Cloudflare Tunnel - Temporary Domain Setup"
echo "=============================================="
echo ""
echo "This will create temporary domains (trycloudflare.com)"
echo "No Cloudflare account or domain needed!"
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed"
    echo "Install it with: sudo apt install cloudflared"
    exit 1
fi

echo "✅ cloudflared is installed"
echo ""

# Check if services are running
echo "Checking if services are running..."
BACKEND_RUNNING=$(curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1 && echo "yes" || echo "no")
FRONTEND_RUNNING=$(curl -s http://localhost:3000 > /dev/null 2>&1 && echo "yes" || echo "no")

if [ "$BACKEND_RUNNING" = "no" ]; then
    echo "⚠️  Backend not running on port 8000"
    echo "   Start it with: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo ""
fi

if [ "$FRONTEND_RUNNING" = "no" ]; then
    echo "⚠️  Frontend not running on port 3000"
    echo "   Start it with: cd frontend && npm run dev"
    echo ""
fi

echo ""
echo "Starting Cloudflare tunnels..."
echo ""

# Start backend tunnel
echo "🔵 Starting Backend Tunnel (port 8000)..."
echo "   This will give you a temporary URL like: https://xxxx-xxxx.trycloudflare.com"
cloudflared tunnel --url http://localhost:8000 &
BACKEND_PID=$!
sleep 3

# Start frontend tunnel
echo ""
echo "🟢 Starting Frontend Tunnel (port 3000)..."
echo "   This will give you a temporary URL like: https://yyyy-yyyy.trycloudflare.com"
cloudflared tunnel --url http://localhost:3000 &
FRONTEND_PID=$!
sleep 3

echo ""
echo "✅ Tunnels started!"
echo ""
echo "📝 Note: The URLs will be displayed above. Look for lines like:"
echo "   +--------------------------------------------------------------------------------------------+"
echo "   |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable): |"
echo "   |  https://xxxx-xxxx.trycloudflare.com                                                       |"
echo "   +--------------------------------------------------------------------------------------------+"
echo ""
echo "⚠️  IMPORTANT:"
echo "   - These URLs are temporary and change each time"
echo "   - They expire after some time of inactivity"
echo "   - Update frontend API config to use backend URL"
echo ""
echo "To stop tunnels, press Ctrl+C or run:"
echo "   kill $BACKEND_PID $FRONTEND_PID"

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

