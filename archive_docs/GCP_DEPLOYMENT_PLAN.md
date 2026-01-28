# 🚀 GCP Deployment Plan - Quick Deployment

## Overview
Deploy Podcast Intelligence System (FastAPI + React) to Google Cloud Platform.

**Target Architecture:**
- **Backend API**: Cloud Run (serverless, auto-scaling)
- **Frontend**: Firebase Hosting (fast CDN, easy SSL)
- **Qdrant**: Cloud Run or GKE (vector database)
- **Neo4j**: Already cloud-hosted (just update connection)
- **Secrets**: Secret Manager (API keys, passwords)

---

## ⚡ Quick Start (30 minutes)

### Prerequisites
```bash
# Install GCP CLI
curl https://sdk.cloud.google.com | bash
gcloud init

# Install Docker
# Install Node.js 18+
```

### Step 1: Setup GCP Project
```bash
# Create project
gcloud projects create podcast-intelligence --name="Podcast Intelligence"
gcloud config set project podcast-intelligence

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firebase.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

## 📦 Deployment Steps

### **1. Backend API (Cloud Run)**

#### 1.1 Create Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install core dependencies (if requirements.txt exists in root)
RUN pip install --no-cache-dir \
    neo4j \
    qdrant-client \
    openai \
    python-dotenv \
    langchain \
    langchain-community \
    langchain-openai \
    numpy \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    pydantic \
    jinja2 \
    aiofiles

# Copy application
COPY . .

# Set environment
ENV PYTHONPATH=/app
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run
CMD exec uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

#### 1.2 Store Secrets
```bash
# Store secrets in Secret Manager
echo -n "your-neo4j-password" | gcloud secrets create neo4j-password --data-file=-
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-qdrant-url" | gcloud secrets create qdrant-url --data-file=-
```

#### 1.3 Build & Deploy
```bash
# Build container
gcloud builds submit --tag gcr.io/podcast-intelligence/api:latest

# Deploy to Cloud Run
gcloud run deploy podcast-api \
  --image gcr.io/podcast-intelligence/api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-secrets NEO4J_PASSWORD=neo4j-password:latest,OPENAI_API_KEY=openai-api-key:latest,QDRANT_URL=qdrant-url:latest \
  --set-env-vars NEO4J_URI=your-neo4j-uri,NEO4J_USER=neo4j
```

---

### **2. Qdrant (Vector Database)**

#### Option A: Cloud Run (Simpler)
```bash
# Deploy Qdrant as Cloud Run service
gcloud run deploy qdrant \
  --image qdrant/qdrant:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --port 6333
```

#### Option B: GKE (More Control)
```bash
# Use existing docker-compose.yml
# Deploy to GKE cluster
gcloud container clusters create qdrant-cluster \
  --num-nodes=1 \
  --machine-type=e2-medium \
  --region=us-central1

# Apply Qdrant deployment
kubectl apply -f k8s/qdrant-deployment.yaml
```

---

### **3. Frontend (Firebase Hosting)**

#### 3.1 Build Frontend
```bash
cd frontend
npm install
npm run build
# Creates dist/ folder
```

#### 3.2 Deploy to Firebase
```bash
# Install Firebase CLI
npm install -g firebase-tools
firebase login

# Initialize Firebase
firebase init hosting

# Select:
# - Use existing project: podcast-intelligence
# - Public directory: dist
# - Single-page app: Yes
# - GitHub Actions: No

# Deploy
firebase deploy --only hosting
```

#### 3.3 Update API URL
```javascript
// frontend/src/services/api.js
// Update base URL to Cloud Run endpoint
const API_BASE_URL = 'https://podcast-api-xxxxx.run.app/api/v1';
```

---

## 🔧 Configuration Files

### `.env` for Cloud Run
```bash
# backend/.env.production
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=from-secret-manager
QDRANT_URL=https://qdrant-xxxxx.run.app
OPENAI_API_KEY=from-secret-manager
WORKSPACE_ID=default
```

### `firebase.json`
```json
{
  "hosting": {
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      }
    ]
  }
}
```

---

## 📋 Deployment Checklist

- [ ] GCP project created
- [ ] APIs enabled
- [ ] Secrets stored in Secret Manager
- [ ] Backend Dockerfile created
- [ ] Backend deployed to Cloud Run
- [ ] Qdrant deployed (Cloud Run or GKE)
- [ ] Frontend built (`npm run build`)
- [ ] Frontend deployed to Firebase
- [ ] API URL updated in frontend
- [ ] CORS configured correctly
- [ ] Environment variables set
- [ ] Health checks working
- [ ] Test API endpoint
- [ ] Test frontend connection

---

## 🚨 Quick Fixes

### CORS Issues
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://podcast-intelligence.web.app",
        "https://podcast-intelligence.firebaseapp.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Port Configuration
```python
# Cloud Run uses PORT env var
import os
port = int(os.getenv("PORT", 8080))
```

### Static Files
```python
# If serving static files
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
```

---

## 💰 Cost Estimate (Monthly)

- **Cloud Run (API)**: ~$20-50 (2GB RAM, 2 CPU, low traffic)
- **Cloud Run (Qdrant)**: ~$30-60 (4GB RAM, 2 CPU)
- **Firebase Hosting**: Free tier (10GB storage, 360MB/day)
- **Secret Manager**: ~$0.06 per secret
- **Total**: ~$50-110/month (low traffic)

---

## 🔄 CI/CD (Optional)

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to GCP

on:
  push:
    branches: [main]

jobs:
  deploy-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/setup-gcloud@v1
      - run: gcloud builds submit --tag gcr.io/podcast-intelligence/api:latest
      - run: gcloud run deploy podcast-api --image gcr.io/podcast-intelligence/api:latest

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: cd frontend && npm install && npm run build
      - uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: ${{ secrets.GITHUB_TOKEN }}
          firebaseServiceAccount: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
```

---

## 🎯 Next Steps

1. **Test locally with Docker**
2. **Deploy backend first** (test API endpoint)
3. **Deploy Qdrant** (test connection)
4. **Deploy frontend** (test full flow)
5. **Monitor logs** in Cloud Console
6. **Set up alerts** for errors

---

## 📞 Support

- **Cloud Run logs**: `gcloud run services logs read podcast-api`
- **Firebase logs**: Firebase Console → Hosting → Logs
- **Debug**: Check Cloud Run console for errors

---

**Estimated Time: 30-60 minutes for initial deployment**

