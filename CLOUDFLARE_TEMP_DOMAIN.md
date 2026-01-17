# 🌐 Cloudflare Tunnel - Temporary Domain Setup

**No domain needed!** Use Cloudflare's free temporary domains for testing.

## 🚀 Quick Start (No Account Needed)

### Option 1: Simple Script (Recommended)

```bash
cd ontology_production_v1
chmod +x cloudflare-tunnel-temp.sh
./cloudflare-tunnel-temp.sh
```

This will:
- Start backend tunnel (port 8000)
- Start frontend tunnel (port 3000)
- Give you temporary URLs like `https://xxxx-xxxx.trycloudflare.com`

### Option 2: Manual Commands

**Terminal 1 - Backend:**
```bash
cloudflared tunnel --url http://localhost:8000
```
You'll get a URL like: `https://abc123-def456.trycloudflare.com`

**Terminal 2 - Frontend:**
```bash
cloudflared tunnel --url http://localhost:3000
```
You'll get a URL like: `https://xyz789-uvw012.trycloudflare.com`

**Terminal 3 - Update Frontend Config:**

Edit `frontend/src/services/api.js` and update the base URL:

```javascript
// Replace with your backend tunnel URL
const API_BASE_URL = 'https://abc123-def456.trycloudflare.com/api/v1'
```

Or use environment variable:
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
```

Then create `.env` file in frontend:
```
VITE_API_URL=https://abc123-def456.trycloudflare.com/api/v1
```

## 📋 Prerequisites

1. **Backend running** on port 8000:
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Frontend running** on port 3000:
   ```bash
   cd frontend
   npm run dev
   ```

3. **cloudflared installed**:
   ```bash
   # Already installed on your system ✅
   ```

## ⚠️ Important Notes

- **Temporary URLs**: These URLs change each time you restart the tunnel
- **Time-limited**: URLs expire after inactivity
- **No HTTPS needed**: Cloudflare provides SSL automatically
- **Public access**: Anyone with the URL can access (for testing only)
- **No authentication**: Not secure for production use

## 🔧 Update Frontend to Use Backend URL

### Method 1: Environment Variable (Recommended)

1. Create `.env` file in `frontend/`:
   ```bash
   VITE_API_URL=https://your-backend-tunnel-url.trycloudflare.com/api/v1
   ```

2. Update `frontend/src/services/api.js`:
   ```javascript
   const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
   ```

3. Restart frontend dev server

### Method 2: Direct Update

Edit `frontend/src/services/api.js`:
```javascript
// Change this line:
const API_BASE_URL = 'http://localhost:8000/api/v1'

// To your backend tunnel URL:
const API_BASE_URL = 'https://abc123-def456.trycloudflare.com/api/v1'
```

## 🎯 Testing

1. Access frontend: `https://your-frontend-url.trycloudflare.com`
2. Test API: `https://your-backend-url.trycloudflare.com/api/v1/health`
3. Check API docs: `https://your-backend-url.trycloudflare.com/api/docs`

## 🛑 Stop Tunnels

Press `Ctrl+C` in the terminal where tunnels are running, or:

```bash
# Find and kill cloudflared processes
pkill cloudflared
```

## 📚 Next Steps

For production, you'll want:
- Your own domain
- Persistent tunnel configuration
- Authentication
- See `CLOUDFLARE_TUNNEL_SETUP.md` for production setup

