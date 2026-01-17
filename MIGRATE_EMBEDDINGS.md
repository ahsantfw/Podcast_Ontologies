# 🔄 Migrate Qdrant Embeddings to GCP

## ⚠️ IMPORTANT: Embeddings Will Be LOST If Not Migrated!

Your local Qdrant has all your embeddings. When you deploy to GCP, you get a **NEW empty Qdrant**. You must migrate first!

---

## 📋 Migration Options

### ✅ **Option 1: Migrate After Deployment (Recommended)**

1. **Deploy Qdrant to GCP** (VM or Cloud Run)
2. **Get GCP Qdrant URL**
3. **Run migration script**

```bash
python migrate_qdrant.py \
    --source http://localhost:6333 \
    --target http://<gcp-qdrant-ip>:6333 \
    --collection ontology_chunks
```

---

### ✅ **Option 2: Re-run Ingestion Script** (Slower, but works)

If migration fails, just re-run your ingestion:

```bash
# Point to GCP Qdrant
export QDRANT_URL=http://<gcp-qdrant-ip>:6333

# Re-run ingestion
python -m core_engine.embeddings.ingest_qdrant
```

**⚠️ This re-embeds everything** (uses OpenAI API again = costs money)

---

## 🚀 Quick Steps

### Step 1: Deploy Qdrant to GCP

**Option A: Cloud Run** (temporary, loses data on restart)
```bash
gcloud run deploy qdrant \
    --image qdrant/qdrant:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 4Gi
```

**Option B: Compute Engine VM** (persistent, recommended)
```bash
# Create VM
gcloud compute instances create qdrant-vm \
    --zone us-central1-a \
    --machine-type e2-standard-4 \
    --boot-disk-size 100GB

# SSH and install Qdrant
gcloud compute ssh qdrant-vm --zone us-central1-a
sudo apt update && sudo apt install -y docker.io
sudo systemctl start docker
sudo docker run -d -p 6333:6333 qdrant/qdrant
```

**Get VM IP:**
```bash
gcloud compute instances describe qdrant-vm \
    --zone us-central1-a \
    --format='value(networkInterfaces[0].networkIP)'
```

---

### Step 2: Run Migration Script

```bash
# Get GCP Qdrant URL
GCP_QDRANT_URL="http://$(gcloud compute instances describe qdrant-vm \
    --zone us-central1-a \
    --format='value(networkInterfaces[0].networkIP)'):6333"

# Run migration
python migrate_qdrant.py \
    --source http://localhost:6333 \
    --target $GCP_QDRANT_URL \
    --collection ontology_chunks
```

---

### Step 3: Update Deployment Script

When deploying backend, use the GCP Qdrant URL:

```bash
read -p "Enter Qdrant URL: " QDRANT_URL
# Enter: http://<vm-ip>:6333
```

---

## 🔍 Verify Migration

```bash
# Check source (local)
curl http://localhost:6333/collections/ontology_chunks

# Check target (GCP)
curl http://<gcp-ip>:6333/collections/ontology_chunks
```

Both should show the same `points_count`.

---

## ❌ What NOT To Do

1. ❌ **Don't deploy Cloud Run Qdrant without migration** → data loss on restart
2. ❌ **Don't use `localhost:6333` in GCP** → won't work
3. ❌ **Don't skip migration** → empty Qdrant = no search results

---

## 💡 Best Practice

**For production:** Use **Compute Engine VM** with persistent disk for Qdrant (not Cloud Run).

**For testing:** Cloud Run is OK if you migrate before each restart.

---

## 🆘 Troubleshooting

**Problem:** Migration script fails
```bash
# Check Qdrant is running
curl http://localhost:6333/health
curl http://<gcp-ip>:6333/health
```

**Problem:** Can't connect to GCP Qdrant from local
```bash
# Check firewall
gcloud compute firewall-rules list | grep qdrant
# If missing, create:
gcloud compute firewall-rules create allow-qdrant \
    --allow tcp:6333 \
    --source-ranges 0.0.0.0/0 \
    --target-tags qdrant
```

**Problem:** Out of memory during migration
```bash
# Reduce batch size
python migrate_qdrant.py \
    --source http://localhost:6333 \
    --target http://<gcp-ip>:6333 \
    --collection ontology_chunks \
    --batch-size 50
```

