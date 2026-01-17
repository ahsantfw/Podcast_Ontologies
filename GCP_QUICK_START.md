# ⚡ GCP Quick Deployment (15 minutes)

## Prerequisites
```bash
# Install tools
curl https://sdk.cloud.google.com | bash  # GCP CLI
npm install -g firebase-tools              # Firebase CLI
```

## One-Command Deployment

```bash
# Run deployment script
./deploy-gcp.sh
```

The script will:
1. ✅ Enable required GCP APIs
2. ✅ Store secrets (Neo4j, OpenAI, Qdrant)
3. ✅ Deploy Qdrant to Cloud Run
4. ✅ Build & deploy backend API
5. ✅ Build & deploy frontend

---

## Manual Steps (if script fails)

### 1. Setup GCP Project
```bash
gcloud projects create podcast-intelligence
gcloud config set project podcast-intelligence
gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com firebase.googleapis.com
```

### 2. Store Secrets
```bash
echo -n "your-neo4j-password" | gcloud secrets create neo4j-password --data-file=-
echo -n "your-openai-key" | gcloud secrets create openai-api-key --data-file=-
```

### 3. Deploy Backend
```bash
# Build
gcloud builds submit --tag gcr.io/podcast-intelligence/api:latest

# Deploy
gcloud run deploy podcast-api \
  --image gcr.io/podcast-intelligence/api:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --set-secrets NEO4J_PASSWORD=neo4j-password:latest,OPENAI_API_KEY=openai-api-key:latest \
  --set-env-vars NEO4J_URI=your-neo4j-uri,NEO4J_USER=neo4j
```

### 4. Deploy Frontend
```bash
cd frontend
npm install && npm run build
firebase init hosting
firebase deploy --only hosting
```

---

## Post-Deployment

### Update Frontend API URL
```javascript
// frontend/src/services/api.js
const API_BASE_URL = 'https://podcast-api-xxxxx.run.app/api/v1';
```

Rebuild and redeploy:
```bash
cd frontend
npm run build
firebase deploy --only hosting
```

---

## Verify Deployment

```bash
# Check API
curl https://podcast-api-xxxxx.run.app/api/v1/health

# Check logs
gcloud run services logs read podcast-api --region us-central1
```

---

## Troubleshooting

### CORS Errors
Update `backend/app/main.py`:
```python
allow_origins=[
    "https://podcast-intelligence.web.app",
    "https://podcast-intelligence.firebaseapp.com"
]
```

### Port Issues
Cloud Run uses `PORT` env var automatically. No changes needed.

### Secret Access
Ensure Cloud Run service account has Secret Manager access:
```bash
gcloud projects add-iam-policy-binding podcast-intelligence \
  --member=serviceAccount:xxxxx@project.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

---

**Time: 15-30 minutes total**

