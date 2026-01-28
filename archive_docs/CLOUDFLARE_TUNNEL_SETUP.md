# 🌐 Cloudflare Tunnel Setup Guide

This guide will help you expose your local application to the internet securely using Cloudflare Tunnel (formerly Argo Tunnel).

## 📋 Prerequisites

1. **Cloudflare Account** (free tier works)
2. **Domain** (can use Cloudflare's free domain or your own)
3. **cloudflared installed** (already installed on your system)

## 🚀 Quick Setup

### Step 1: Login to Cloudflare

```bash
cloudflared tunnel login
```

This will open a browser window. Select your domain and authorize the tunnel.

### Step 2: Create a Tunnel

```bash
cloudflared tunnel create kg-tunnel
```

This will create a tunnel and save credentials to `~/.cloudflared/<tunnel-id>.json`

### Step 3: Create DNS Record

```bash
# For frontend
cloudflared tunnel route dns kg-tunnel your-app.your-domain.com

# For backend API (optional, can use path-based routing)
cloudflared tunnel route dns kg-tunnel api.your-app.your-domain.com
```

### Step 4: Configure Tunnel

Edit `cloudflare-tunnel.yml` and replace:
- `your-tunnel-id` with your actual tunnel ID (from Step 2)
- `your-app.your-domain.com` with your domain
- Update credentials-file path if needed

### Step 5: Run Tunnel

```bash
# Run tunnel in foreground (for testing)
cloudflared tunnel --config cloudflare-tunnel.yml run kg-tunnel

# Or run as service (recommended for production)
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

## 🔧 Alternative: Single Domain Setup

If you want to use a single domain with path-based routing:

```yaml
tunnel: your-tunnel-id
credentials-file: /home/tayyab/.cloudflared/your-tunnel-id.json

ingress:
  # Backend API routes
  - hostname: your-app.your-domain.com
    path: /api/*
    service: http://localhost:8000
  
  # Frontend routes
  - hostname: your-app.your-domain.com
    service: http://localhost:3000
```

## 📝 Update Frontend API Configuration

After setting up the tunnel, update your frontend to use the tunnel URL:

**File**: `frontend/src/services/api.js`

```javascript
// For subdomain setup
const API_BASE_URL = 'https://api.your-app.your-domain.com/api/v1'

// OR for path-based setup
const API_BASE_URL = 'https://your-app.your-domain.com/api/v1'
```

## 🎯 Benefits

✅ **HTTPS automatically** - Cloudflare provides SSL certificates  
✅ **No port forwarding** - No need to open firewall ports  
✅ **DDoS protection** - Built-in Cloudflare protection  
✅ **Free tier available** - No cost for basic usage  
✅ **Secure** - Encrypted connection to Cloudflare  

## 🔍 Troubleshooting

### Check tunnel status
```bash
cloudflared tunnel info kg-tunnel
```

### View tunnel logs
```bash
cloudflared tunnel --config cloudflare-tunnel.yml run kg-tunnel --loglevel debug
```

### Test connection
```bash
curl https://your-app.your-domain.com/api/v1/health
```

## 📚 Resources

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Tunnel GitHub](https://github.com/cloudflare/cloudflared)

