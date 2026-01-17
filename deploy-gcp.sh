#!/bin/bash
# Quick GCP Deployment Script
# Run: ./deploy-gcp.sh

set -e

echo "🚀 Starting GCP Deployment..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="podcast-intelligence"
REGION="us-central1"
API_SERVICE="podcast-api"
QDRANT_SERVICE="qdrant"
FRONTEND_DIR="frontend"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v gcloud >/dev/null 2>&1 || { echo -e "${RED}gcloud CLI not found. Install: https://cloud.google.com/sdk${NC}" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker not found. Install Docker first.${NC}" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo -e "${RED}npm not found. Install Node.js first.${NC}" >&2; exit 1; }

# Set project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firebase.googleapis.com

# Step 1: Store Secrets
echo -e "${YELLOW}Step 1: Storing secrets...${NC}"
read -p "Enter Neo4j password: " -s NEO4J_PASS
echo ""
read -p "Enter OpenAI API key: " -s OPENAI_KEY
echo ""
read -p "Enter Qdrant URL (or press Enter to deploy new): " QDRANT_URL

echo -n "$NEO4J_PASS" | gcloud secrets create neo4j-password --data-file=- 2>/dev/null || \
  echo -n "$NEO4J_PASS" | gcloud secrets versions add neo4j-password --data-file=-

echo -n "$OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=- 2>/dev/null || \
  echo -n "$OPENAI_KEY" | gcloud secrets versions add openai-api-key --data-file=-

if [ ! -z "$QDRANT_URL" ]; then
  echo -n "$QDRANT_URL" | gcloud secrets create qdrant-url --data-file=- 2>/dev/null || \
    echo -n "$QDRANT_URL" | gcloud secrets versions add qdrant-url --data-file=-
fi

# Step 2: Deploy Qdrant (if not provided)
if [ -z "$QDRANT_URL" ]; then
  echo -e "${YELLOW}Step 2: Deploying Qdrant...${NC}"
  gcloud run deploy $QDRANT_SERVICE \
    --image qdrant/qdrant:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --port 6333 \
    --quiet
  
  QDRANT_URL=$(gcloud run services describe $QDRANT_SERVICE --region $REGION --format 'value(status.url)')
  echo -e "${GREEN}Qdrant deployed at: $QDRANT_URL${NC}"
fi

# Step 3: Build & Deploy Backend
echo -e "${YELLOW}Step 3: Building backend Docker image...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/$API_SERVICE:latest

echo -e "${YELLOW}Step 4: Deploying backend API...${NC}"
read -p "Enter Neo4j URI: " NEO4J_URI
read -p "Enter Neo4j User (default: neo4j): " NEO4J_USER
NEO4J_USER=${NEO4J_USER:-neo4j}

gcloud run deploy $API_SERVICE \
  --image gcr.io/$PROJECT_ID/$API_SERVICE:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-secrets NEO4J_PASSWORD=neo4j-password:latest,OPENAI_API_KEY=openai-api-key:latest,QDRANT_URL=qdrant-url:latest \
  --set-env-vars NEO4J_URI=$NEO4J_URI,NEO4J_USER=$NEO4J_USER,WORKSPACE_ID=default \
  --quiet

API_URL=$(gcloud run services describe $API_SERVICE --region $REGION --format 'value(status.url)')
echo -e "${GREEN}Backend API deployed at: $API_URL${NC}"

# Step 5: Build Frontend
echo -e "${YELLOW}Step 5: Building frontend...${NC}"
cd $FRONTEND_DIR
npm install

# Create .env.production with API URL
echo "VITE_API_URL=$API_URL/api/v1" > .env.production
echo -e "${GREEN}Created .env.production with API URL: $API_URL/api/v1${NC}"

npm run build
cd ..

# Step 6: Deploy Frontend
echo -e "${YELLOW}Step 6: Deploying frontend...${NC}"
if [ ! -f "firebase.json" ]; then
  echo "Initializing Firebase..."
  firebase init hosting --project $PROJECT_ID --public dist --yes
fi

firebase deploy --only hosting --project $PROJECT_ID

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}API URL: $API_URL${NC}"
echo -e "${GREEN}Frontend: Check Firebase Console for URL${NC}"

