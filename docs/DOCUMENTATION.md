# Complete A–Z Documentation — Podcast Intelligence System

Production-ready documentation for the Ontology Production / Podcast Intelligence system. Covers every aspect from setup to deployment.

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Indexing Phase](#3-indexing-phase)
4. [Retrieval Phase](#4-retrieval-phase)
5. [Project Structure](#5-project-structure)
6. [Prerequisites](#6-prerequisites)
7. [Environment Variables](#7-environment-variables)
8. [Installation](#8-installation)
9. [Running the System](#9-running-the-system)
10. [API Reference](#10-api-reference)
11. [Core Engine Modules](#11-core-engine-modules)
12. [Frontend](#12-frontend)
13. [Data Models](#13-data-models)
14. [Configuration](#14-configuration)
15. [Deployment](#15-deployment)
16. [Development Guide](#16-development-guide)
17. [Extra Scripts](#17-extra-scripts)
18. [Troubleshooting](#18-troubleshooting)
19. [Glossary](#19-glossary)

---

## 1. Overview

The **Podcast Intelligence System** is an AI-powered platform that:

- **Ingests** podcast transcripts (`.txt` files)
- **Extracts** structured knowledge (concepts, relationships, quotes) via GPT-4
- **Stores** in a knowledge graph (Neo4j) and vector store (Qdrant)
- **Queries** via natural language with an agent that uses RAG + KG
- **Explores** the knowledge graph and generates thematic scripts

### Key Features

| Feature | Description |
|---------|-------------|
| Multi-workspace | Isolated data per workspace |
| Streaming | Server-sent events for real-time answers |
| Style & tone | Casual/professional, warm/neutral |
| Sessions | Conversation history per session |
| Script generation | Tapestry, thematic, linear styles |

### Two Phases

1. **Indexing** — Load transcripts → chunk → extract KG → embed → store in Neo4j + Qdrant  
2. **Retrieval** — User query → plan → RAG + KG retrieval → rerank → synthesize → answer

---

## 2. System Architecture

```
┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend   │────►│   Backend    │────►│ Core Engine │
│  (React)     │     │  (FastAPI)   │     │             │
└──────────────┘     └──────┬───────┘     └──────┬──────┘
                            │                    │
                    ┌───────┴────────────────────┴───────┐
                    │  Neo4j  │  Qdrant  │  OpenAI       │
                    └───────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams and data flow.

---

## 3. Indexing Phase

When you upload and process transcripts:

| Step | Component | What Happens |
|------|-----------|--------------|
| 1 | `ingestion/loader` | Discover and load `.txt` files as LangChain Documents |
| 2 | `chunking/chunker` | Split into chunks (2000 chars, 200 overlap), dialogue-aware |
| 3 | `kg/extractor` | GPT-4 extracts concepts, relationships, quotes |
| 4 | `kg/normalizer` | Normalize IDs, deduplicate, link to existing nodes |
| 5 | `kg/writer` | Write to Neo4j (MERGE nodes/relationships) |
| 6 | `embeddings/ingest_qdrant` | Embed chunks, upsert to Qdrant |
| 7 | `kg/cross_episode` | Link concepts across episodes |

**Entry point:** `POST /ingest/upload` → `POST /ingest/process`

---

## 4. Retrieval Phase

When a user asks a question:

| Step | Component | What Happens |
|------|-----------|--------------|
| 1 | `intelligent_query_planner` | Plan query (relevance, complexity, strategy) |
| 2 | `retrieve_rag_node` | HybridRetriever vector search (Qdrant) |
| 3 | `retrieve_kg_node` | Neo4j graph search via agent |
| 4 | `reranker` | RRF + MMR merge and rerank |
| 5 | `synthesize_node` | LLM generates answer from context |
| 6 | `self_reflect_node` | Quality check |

See [RETRIEVAL_FILES_EXPLAINED.md](RETRIEVAL_FILES_EXPLAINED.md) for file-by-file details.

---

## 5. Project Structure

```
ontology_production_v1/
├── backend/                 # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/      # query, ingestion, graph, scripts, workspace, sessions
│   │   ├── core/            # reasoner_pool, workspace
│   │   ├── database/        # job_db, session_db
│   │   └── services/        # ingestion_service
│   └── requirements.txt
├── core_engine/             # Business logic
│   ├── chunking/            # chunker.py
│   ├── embeddings/          # ingest_qdrant.py
│   ├── ingestion/           # loader.py
│   ├── kg/                  # extractor, neo4j_client, normalizer, writer, etc.
│   ├── reasoning/           # agent, hybrid_retriever, langgraph_*, etc.
│   └── script_generation/   # script_generator, narrative_builder, etc.
├── frontend/                # React SPA
│   └── src/
│       ├── pages/           # Chat, Dashboard, Upload, Explore, Scripts
│       └── services/api.js
├── data/
│   └── workspaces/{id}/transcripts/
├── docs/                    # Documentation
├── extra/                   # Testing, debug, utility scripts (not core)
├── configs/                 # logging.yaml
├── logs/                    # app.log
├── docker-compose.yml       # Qdrant
└── .env                     # Environment (create this)
```

---

## 6. Prerequisites

| Requirement | Version / Notes |
|-------------|-----------------|
| Python | 3.10+ |
| Node.js | 18+ (for frontend) |
| Docker | For Qdrant |
| Neo4j | 4.x or 5.x (local or Aura Cloud) |
| OpenAI API key | Required |

---

## 7. Environment Variables

Create `.env` at project root:

```bash
# Required — OpenAI
OPENAI_API_KEY=sk-...

# Qdrant (vector store)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=ontology_chunks
QDRANT_API_KEY=              # Optional for local

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
AURA_INSTANCEID=your-instance-id
AURA_INSTANCENAME=Instance01

# LangSmith (optional — observability)
LANGCHAIN_TRACING_V2=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com/
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=your-project-name

# Retrieval
USE_LANGGRAPH=true
RERANKING_STRATEGY=rrf_mmr   # rrf, mmr, or rrf_mmr
```

### Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM and embeddings |
| `QDRANT_URL` | Yes | Qdrant URL (e.g. http://localhost:6333) |
| `QDRANT_COLLECTION` | No | Default collection name (default: ontology_chunks) |
| `QDRANT_API_KEY` | No | Qdrant API key (for cloud) |
| `WORKSPACE_ID` | No | Default workspace (default: default) |
| `EMBED_MODEL` | No | Embedding model (default: text-embedding-3-large) |
| `NEO4J_URI` | Yes | Neo4j bolt URI (bolt:// or neo4j+s:// for Aura) |
| `NEO4J_USERNAME` | Yes | Neo4j username |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `NEO4J_DATABASE` | No | Neo4j database (default: neo4j) |
| `USE_LANGGRAPH` | No | Enable LangGraph workflow (default: true) |
| `RERANKING_STRATEGY` | No | rrf, mmr, or rrf_mmr (default: rrf_mmr) |
| `LANGCHAIN_TRACING_V2` | No | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name |

---

## 8. Installation

### Backend

```bash
pip install -r backend/requirements.txt
pip install openai langchain langchain-openai langchain-text-splitters langchain-core
pip install qdrant-client neo4j python-dotenv langgraph
```

### Frontend

```bash
cd frontend
npm install
```

### Qdrant

```bash
docker-compose up -d qdrant
```

---

## 9. Running the System

| Service | Command | URL |
|---------|---------|-----|
| Qdrant | `docker-compose up -d qdrant` | http://localhost:6333 |
| Backend | `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000` | http://localhost:8000 |
| Frontend | `cd frontend && npm run dev` | http://localhost:3000 |

**Order:** Start Qdrant and Neo4j first, then backend, then frontend.

---

## 10. API Reference

**Base URL:** `http://localhost:8000/api/v1`  
**Header:** `X-Workspace-Id` (optional, default: `default`)

### Query

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | Natural language query (JSON) |
| POST | `/query/stream` | Streaming query (SSE) |
| GET | `/query/history?session_id=` | Conversation history |

**Query Request:**

```json
{
  "question": "What practices improve creativity?",
  "workspace_id": "default",
  "session_id": "uuid",
  "style": "casual",
  "tone": "warm"
}
```

**Query Response:**

```json
{
  "answer": "...",
  "sources": [{"text": "...", "episode_id": "...", "speaker": "..."}],
  "metadata": {"method": "agent", "rag_count": 5, "kg_count": 3},
  "session_id": "uuid"
}
```

### Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingest/upload` | Upload files (multipart/form-data, key `files`) |
| POST | `/ingest/process` | Start processing `{"upload_id": "...", "clear_existing": false}` |
| GET | `/ingest/status/{job_id}` | Job status and progress |

### Graph

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/graph/stats` | KG statistics |
| GET | `/graph/concepts?theme=&concept_type=&limit=50` | List concepts |
| GET | `/graph/concepts/{id}` | Concept detail + relationships |

### Scripts

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scripts/generate` | `{"theme": "...", "runtime_minutes": 45, "style": "tapestry", "format": "markdown"}` |

### Workspaces & Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workspaces` | Create workspace |
| GET | `/workspaces` | List workspaces |
| DELETE | `/workspaces/{id}/kg` | Delete KG only |
| DELETE | `/workspaces/{id}/embeddings` | Delete embeddings only |
| DELETE | `/workspaces/{id}/all` | Delete KG + embeddings |
| GET | `/sessions` | List sessions |
| DELETE | `/sessions/{id}` | Delete session |

**API docs (Swagger):** http://localhost:8000/api/docs

---

## 11. Core Engine Modules

### Ingestion

- **loader.py** — `load_transcripts()`, `discover_transcripts()`, `load_with_langchain()`  
  Loads `.txt` files as LangChain Documents with metadata.

### Chunking

- **chunker.py** — Dialogue-aware chunking (2000 chars, 200 overlap).  
  Supports `[hh:mm:ss] - Speaker` and `SPEAKER:` formats.

### Embeddings

- **ingest_qdrant.py** — Batch embed with OpenAI, upsert to Qdrant.  
  Collection: `{workspace_id}_chunks`.

### KG

- **extractor.py** — LLM extraction (concepts, relationships, quotes)  
- **normalizer.py** — Deduplication, alias linking  
- **writer.py** — Neo4j MERGE with provenance  
- **neo4j_client.py** — Connection, execute_read/execute_write  
- **schema.py** — Node labels, relationship types, constraints, indexes  
- **prompts.py** — Extraction prompts  
- **schemas.py** — JSON schema validation  
- **cross_episode.py** — Cross-episode linking  

### Reasoning

- **reasoning.py** — KGReasoner, main query orchestrator  
- **agent.py** — PodcastAgent (LLM-driven)  
- **hybrid_retriever.py** — Qdrant + Neo4j hybrid  
- **langgraph_workflow.py** — Retrieval workflow  
- **intelligent_query_planner.py** — Query planning  
- **reranker.py** — RRF + MMR  
- **session_manager.py** — Conversation history  
- **style_config.py**, **tone_config.py** — Response style/tone  

### Script Generation

- **script_generator.py** — Theme → quotes → narrative → format  
- **theme_extractor.py**, **quote_compiler.py**, **narrative_builder.py**, **formatter.py**

---

## 12. Frontend

- **Framework:** React 18 + Vite  
- **Routing:** `/`, `/chat`, `/dashboard`, `/upload`, `/scripts`, `/explore`, `/account`  
- **State:** WorkspaceContext (workspace_id in localStorage)  
- **API:** `api.js` — queryAPI, scriptsAPI, ingestionAPI, graphAPI, workspaceAPI, sessionsAPI  

**Environment:** `VITE_API_URL` — Backend API base (default: proxied `/api`)

---

## 13. Data Models

### Concept (Neo4j)

`id`, `name`, `type`, `description`, `workspace_id`, `episode_ids`, `source_paths`, provenance

### Relationship (Neo4j)

Types: CAUSES, INFLUENCES, OPTIMIZES, ENABLES, REDUCES, LEADS_TO, REQUIRES, RELATES_TO, IS_PART_OF  
Properties: `confidence`, provenance

### Chunk (Qdrant)

Vector + payload: `episode_id`, `source_path`, `chunk_index`, `workspace_id`, `text`, metadata

### Job (SQLite)

`job_id`, `workspace_id`, `status`, `progress`, `results`, `error`

---

## 14. Configuration

| Config | Location |
|--------|----------|
| Logging | `configs/logging.yaml`, `core_engine/logging.py` |
| Logs | `logs/app.log` |
| Reasoner pool | `backend/app/core/reasoner_pool.py` (30 min idle timeout) |

---

## 15. Deployment

### Local / VM

1. Install dependencies (see [Installation](#8-installation))  
2. Set up Neo4j and Qdrant (Docker or cloud)  
3. Configure `.env`  
4. Run backend with `uvicorn` (or gunicorn for production)  
5. Build frontend: `cd frontend && npm run build`  
6. Serve frontend static files (nginx, etc.)

### Docker

- `docker-compose.yml` includes Qdrant. Add Neo4j and app services as needed.  
- See `deploy-gcp.sh` and `setup-cloudflare-tunnel.sh` for GCP/Cloudflare options.

---

## 16. Development Guide

1. **Backend:** Run with `--reload` for auto-restart  
2. **Frontend:** `npm run dev` with HMR  
3. **Logs:** Check `logs/app.log`  
4. **API docs:** http://localhost:8000/api/docs  
5. **Scripts in extra/:** Run from project root: `python extra/script_name.py`

---

## 17. Extra Scripts

Located in `extra/` (not required for core app):

| Script | Purpose |
|--------|---------|
| `main.py` | Standalone pipeline (process + query) |
| `query_kg.py` | Standalone query script |
| `test_*.py` | Unit/integration tests |
| `debug_*.py` | Debug utilities |
| `validate_env.py`, `verify_env.py` | Environment checks |
| `cleanup_database.py`, `migrate_qdrant.py` | DB utilities |

Run from project root: `python extra/script_name.py`

---

## 18. Troubleshooting

| Issue | Fix |
|-------|-----|
| No transcripts found | Files in `data/workspaces/{id}/transcripts/`, format `.txt` |
| Qdrant connection failed | `docker-compose up -d qdrant` |
| Neo4j connection failed | Check URI, user, password; use Aura bolt URL if cloud |
| OpenAI errors | Verify API key, check quota |
| Streaming not working | `X-Accel-Buffering: no` for nginx; check CORS |
| No quotes found (scripts) | Re-run ingestion; try broader theme |

---

## 19. Glossary

| Term | Meaning |
|------|---------|
| **KG** | Knowledge Graph (Neo4j) |
| **RAG** | Retrieval-Augmented Generation |
| **Hybrid retrieval** | Vector (Qdrant) + graph (Neo4j) combined |
| **Workspace** | Isolated tenant with own transcripts, KG, embeddings |
| **Provenance** | Source tracking (episode_id, speaker, chunk) |
| **LangGraph** | State machine for retrieval workflow |

---

*Production-ready documentation. Last updated: February 2025.*
