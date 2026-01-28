# 🚀 Start Qdrant & Create Embeddings (Quick Guide)

## Step 1: Start Qdrant with Docker

Run this command in terminal:

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

**Explanation:**
- `-d` = run in background (detached)
- `--name qdrant` = container name
- `-p 6333:6333` = Qdrant API port
- `-p 6334:6334` = Qdrant Web UI port
- `-v $(pwd)/qdrant_storage:/qdrant/storage` = persistent storage (saves data)
- `qdrant/qdrant:latest` = official Qdrant image

---

## Step 2: Verify Qdrant is Running

```bash
# Check container is running
docker ps | grep qdrant

# Check Qdrant health
curl http://localhost:6333/health

# Open Qdrant Web UI (optional)
open http://localhost:6334
```

**Expected output:**
```json
{"title":"qdrant - vector search engine","version":"1.x.x"}
```

---

## Step 3: Create Embeddings Only (Skip KG)

**If transcripts are in `data/transcripts/`:**

```bash
python process_with_metrics_async.py \
    --workspace default \
    --transcripts-dir data/transcripts \
    --skip-kg \
    --max-concurrent 30 \
    --batch-size 15
```

**If transcripts are in `data/workspaces/default/transcripts/` (default location):**

```bash
python process_with_metrics_async.py \
    --workspace default \
    --skip-kg \
    --max-concurrent 30 \
    --batch-size 15
```

**Explanation:**
- `--workspace default` = workspace ID
- `--transcripts-dir data/transcripts` = **point to your transcripts folder**
- `--skip-kg` = **skip knowledge graph extraction** (only create embeddings)
- `--max-concurrent 30` = 30 parallel API calls
- `--batch-size 15` = 15 chunks per batch

---

## Alternative: Minimal Command

**For `data/transcripts/`:**

```bash
python process_with_metrics_async.py --transcripts-dir data/transcripts --skip-kg
```

**For default location:**

```bash
python process_with_metrics_async.py --skip-kg
```

---

## Check Embeddings Created

After running, verify in Qdrant:

```bash
# List collections
curl http://localhost:6333/collections

# Check collection info
curl http://localhost:6333/collections/default_chunks
```

---

## Stop Qdrant (when done)

```bash
docker stop qdrant
docker rm qdrant
```

---

## Common Issues

**Problem:** Port 6333 already in use
```bash
# Find process using port 6333
lsof -i :6333

# Kill it or use different port:
docker run -d -p 6335:6333 qdrant/qdrant
# Then set QDRANT_URL=http://localhost:6335 in .env
```

**Problem:** Docker not installed
```bash
# Install Docker Desktop or use:
sudo apt-get install docker.io
sudo systemctl start docker
```

**Problem:** Out of memory
```bash
# Reduce concurrent calls:
python process_with_metrics_async.py \
    --skip-kg \
    --max-concurrent 10 \
    --batch-size 5
```

---

## Quick Reference

| Task | Command |
|------|---------|
| **Start Qdrant** | `docker run -d --name qdrant -p 6333:6333 qdrant/qdrant` |
| **Check Qdrant** | `curl http://localhost:6333/health` |
| **Create Embeddings** | `python process_with_metrics_async.py --skip-kg` |
| **Stop Qdrant** | `docker stop qdrant` |

