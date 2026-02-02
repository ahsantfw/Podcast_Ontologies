# Quick Start Guide

Get the **Podcast Intelligence System** running in under 15 minutes. Production-ready setup.

---

## Prerequisites

| Requirement | Version / Notes |
|-------------|-----------------|
| **Python** | 3.10+ |
| **Node.js** | 18+ (for frontend) |
| **Docker** | For Qdrant |
| **Neo4j** | 4.x or 5.x (local or [Neo4j Aura](https://neo4j.com/cloud/aura/)) |
| **OpenAI API key** | Required |

---

## Step 1: Clone & Environment

```bash
cd ontology_production_v1
```

Create `.env` in the project root:

```bash
# Required — OpenAI
OPENAI_API_KEY=sk-your-key-here

# Qdrant (vector store)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=ontology_chunks
QDRANT_API_KEY=   # Optional for local

# Workspace & Embeddings
WORKSPACE_ID=default
EMBED_MODEL=text-embedding-3-large

# Neo4j (knowledge graph)
# Local: bolt://localhost:7687 | Aura: neo4j+s://xxxx.databases.neo4j.io
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# Neo4j Aura (optional — if using Aura Cloud)
# AURA_INSTANCEID=your-instance-id
# AURA_INSTANCENAME=Instance01

# LangSmith (optional — observability)
# LANGCHAIN_TRACING_V2=true
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com/
# LANGCHAIN_API_KEY=lsv2_pt_...
# LANGCHAIN_PROJECT=your-project-name

# Retrieval
USE_LANGGRAPH=true
RERANKING_STRATEGY=rrf_mmr   # rrf, mmr, or rrf_mmr
```

---

## Step 2: Install Dependencies

### Backend

```bash
# Core FastAPI
pip install -r backend/requirements.txt

# Core engine & integrations
pip install openai langchain langchain-openai langchain-text-splitters langchain-core
pip install qdrant-client neo4j python-dotenv
pip install langgraph  # Required for retrieval workflow
```

### Frontend

```bash
cd frontend
npm install
```

---

## Step 3: Start External Services

### Qdrant (Vector Store)

```bash
docker-compose up -d qdrant
```

### Neo4j

- **Local**: Run Neo4j Desktop or Docker on `bolt://localhost:7687`
- **Aura**: Create a free instance at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/) and set `NEO4J_URI` to the provided bolt URL

---

## Step 4: Run the Backend API

From project root:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**API base:** http://localhost:8000  
**Swagger docs:** http://localhost:8000/api/docs  
**Health check:** http://localhost:8000/api/v1/health

---

## Step 5: Run the Frontend

```bash
cd frontend
npm run dev
```

**App:** http://localhost:3000

The frontend proxies `/api` to the backend automatically.

---

## Step 6: First Workflow

1. Open http://localhost:3000/upload
2. Upload `.txt` transcript files
3. Click **Process** — wait for job to complete
4. Go to **Chat** and ask: *"What practices improve creativity?"*

---

## Verify Setup

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Expected: {"status":"healthy"}
```

---

## Quick Reference

| Service | Command | URL |
|---------|---------|-----|
| Qdrant | `docker-compose up -d qdrant` | http://localhost:6333 |
| Backend | `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000` | http://localhost:8000 |
| Frontend | `cd frontend && npm run dev` | http://localhost:3000 |

---

## Common Issues

| Issue | Fix |
|-------|-----|
| Qdrant connection failed | `docker-compose up -d qdrant` |
| Neo4j connection failed | Check `NEO4J_URI`, user, password |
| No transcripts found | Put `.txt` files in `data/workspaces/default/transcripts/` |
| OpenAI errors | Verify `OPENAI_API_KEY` and quota |

---

## Next Steps

- [ARCHITECTURE.md](ARCHITECTURE.md) — System design and diagrams
- [DOCUMENTATION.md](DOCUMENTATION.md) — Complete A–Z documentation
