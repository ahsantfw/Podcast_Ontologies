# Podcast Intelligence System

**Production-ready** AI platform for ingesting podcast transcripts, extracting structured knowledge, and querying insights via natural language. Built with FastAPI, React, Neo4j, Qdrant, and OpenAI.

---

## Features

- **Knowledge Graph** — Extract concepts, relationships, and quotes from transcripts using GPT-4
- **Hybrid Retrieval** — Combine vector search (Qdrant) and graph traversal (Neo4j) for better answers
- **Natural Language QA** — Ask questions in plain English; an agent uses RAG + KG tools
- **Streaming Responses** — Server-sent events for real-time answer streaming
- **Multi-Workspace** — Isolated data per workspace (transcripts, KG, embeddings)
- **Script Generation** — Generate thematic scripts (tapestry, thematic, linear) from the knowledge graph
- **Graph Exploration** — Browse concepts, relationships, and cross-episode links

---

## Quick Links

| Document | Description |
|----------|-------------|
| [docs/QUICK_START.md](docs/QUICK_START.md) | Get up and running in 15 minutes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture diagrams and component overview |
| [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) | Complete A–Z documentation |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Python 3.10+ |
| Frontend | React, Vite |
| Knowledge Graph | Neo4j |
| Vector Store | Qdrant |
| LLM & Embeddings | OpenAI (GPT-4, text-embedding-3-large) |

---

## Project Structure

```
ontology_production_v1/
├── backend/           # FastAPI REST API
├── core_engine/       # Ingestion, KG extraction, reasoning, script generation
├── frontend/          # React SPA
├── data/              # Transcripts, workspaces
├── docs/              # Documentation (Quick Start, Architecture, A–Z)
├── extra/             # Testing, debug, and utility scripts (not required for core app)
├── configs/           # Logging configuration
└── docker-compose.yml # Qdrant service
```

---

## Getting Started

1. **Install dependencies**

   ```bash
   pip install -r backend/requirements.txt
   pip install openai langchain langchain-openai langchain-text-splitters langchain-core qdrant-client neo4j python-dotenv langgraph
   cd frontend && npm install
   ```

2. **Configure `.env`** (project root)

   ```
   OPENAI_API_KEY=sk-...
   QDRANT_URL=http://localhost:6333
   QDRANT_COLLECTION=ontology_chunks
   WORKSPACE_ID=default
   EMBED_MODEL=text-embedding-3-large
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your_password
   NEO4J_DATABASE=neo4j
   USE_LANGGRAPH=true
   RERANKING_STRATEGY=rrf_mmr
   ```
   See [docs/QUICK_START.md](docs/QUICK_START.md) for the full list.

3. **Start services**

   ```bash
   docker-compose up -d qdrant
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   cd frontend && npm run dev
   ```

4. **Upload transcripts** at http://localhost:3000/upload, process them, then query in Chat.

For detailed steps, see [docs/QUICK_START.md](docs/QUICK_START.md).

---

## License

Proprietary. All rights reserved.
