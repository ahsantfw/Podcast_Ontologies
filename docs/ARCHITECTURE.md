# Architecture Diagrams — Podcast Intelligence System

This document describes how the **Ontology Production / Podcast Intelligence** system is structured and how each component works together.

---

## 1. High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              PODCAST INTELLIGENCE SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌──────────────┐     HTTP/SSE      ┌──────────────────┐     Python API     ┌─────────┐│
│   │   FRONTEND   │◄─────────────────►│     BACKEND      │◄──────────────────►│  CORE   ││
│   │  (React/Vite)│                   │  (FastAPI 8000)  │                    │ ENGINE  ││
│   └──────────────┘                   └────────┬─────────┘                    └────┬────┘│
│         │                                      │                                    │    │
│         │                                      │                                    │    │
│         └──────────────────────────────────────┼────────────────────────────────────┘    │
│                                                │                                         │
│   ┌────────────────────────────────────────────┼─────────────────────────────────────┐  │
│   │                    EXTERNAL SERVICES        │                                      │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │                                      │  │
│   │  │  Neo4j   │  │ Qdrant   │  │  OpenAI  │◄─┘                                      │  │
│   │  │ (Graph)  │  │(Vectors) │  │ (LLM)    │                                         │  │
│   │  └──────────┘  └──────────┘  └──────────┘                                         │  │
│   └───────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                                      │
│  • React SPA (Chat, Dashboard, Upload, Explore, Scripts)                             │
│  • WorkspaceContext (workspace isolation)                                            │
│  • API client (axios) with X-Workspace-Id header                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER (FastAPI)                                     │
│  • /api/v1/query, /query/stream    → Natural language Q&A                            │
│  • /api/v1/ingest/upload, process  → Transcript ingestion                            │
│  • /api/v1/graph/*                 → Graph exploration (stats, concepts)             │
│  • /api/v1/scripts/generate        → Script generation from KG                       │
│  • /api/v1/workspaces, sessions    → Workspace & session management                  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CORE ENGINE                                             │
│  • reasoning/     → Agent, HybridRetriever, LangGraph workflow                       │
│  • kg/            → Neo4j client, extractor, normalizer, writer, cross_episode       │
│  • chunking/      → Dialogue-aware chunking                                          │
│  • embeddings/    → Qdrant ingestion                                                 │
│  • ingestion/     → Transcript loader                                                │
│  • script_generation/ → Tapestry-style script generator                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                              │
│  • Neo4j     → Knowledge graph (concepts, relationships, quotes)                     │
│  • Qdrant    → Vector embeddings (semantic search)                                   │
│  • SQLite    → Sessions, jobs (data/sessions.db, JobDB)                              │
│  • File system → Transcripts (data/workspaces/{id}/transcripts/)                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Ingestion Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION PIPELINE (Background Job)                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

   User uploads .txt
         │
         ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  1. LOAD            │     │  2. CHUNK           │     │  3. KG EXTRACTION   │
│  ingestion/loader   │────►│  chunking/chunker   │────►│  kg/extractor       │
│  • discover .txt    │     │  • dialogue-aware   │     │  • GPT-4o extraction │
│  • load as Docs     │     │  • 2000 chars, 200  │     │  • concepts, rels,   │
│  • metadata         │     │    overlap          │     │    quotes            │
└─────────────────────┘     └─────────────────────┘     └──────────┬──────────┘
                                                                   │
         ┌─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  4. NORMALIZE       │     │  5. WRITE NEO4J     │     │  6. EMBED & QDRANT  │
│  kg/normalizer      │────►│  kg/writer          │────►│  embeddings/        │
│  • dedupe concepts  │     │  • MERGE nodes      │     │  ingest_qdrant      │
│  • link aliases     │     │  • provenance       │     │  • text-embedding-3 │
└─────────────────────┘     └─────────────────────┘     └──────────┬──────────┘
                                                                   │
                                                                   ▼
                                                         ┌─────────────────────┐
                                                         │  7. CROSS-EPISODE   │
                                                         │  kg/cross_episode   │
                                                         │  • link concepts    │
                                                         │    across episodes  │
                                                         └─────────────────────┘
```

---

## 4. Query / Reasoning Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           QUERY FLOW (Agent-Driven)                                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

   User question
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         PODCAST AGENT (LLM Brain)                                        │
│  • Understands intent                                                                   │
│  • Decides: RAG, KG, or both                                                            │
│  • Synthesizes final answer                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────┬──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐    ┌─────────────────────────┐    ┌─────────────────┐
│  RAG Tool       │    │  KG Tool                │    │  Memory         │
│  (Qdrant)       │    │  (Neo4j)                │    │  (Session)      │
│  • vector search│    │  • Cypher queries       │    │  • conversation │
│  • query expand │    │  • multi-hop            │    │    history      │
└────────┬────────┘    └────────────┬────────────┘    └─────────────────┘
         │                          │
         │    ┌─────────────────────┘
         ▼    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         HYBRID RETRIEVER                                                 │
│  • Combines vector (Qdrant) + graph (Neo4j) results                                     │
│  • Reranks merged results                                                               │
│  • Returns top_k chunks with metadata                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         SYNTHESIS                                                        │
│  • LLM generates answer from retrieved context                                          │
│  • Sources with episode_id, speaker, timestamp                                          │
│  • Style/tone (casual/professional, warm/neutral)                                       │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. LangGraph Workflow (Optional Path)

When LangGraph is available, retrieval can follow this state machine:

```
                    ┌──────────────────────────────────────────────────────┐
                    │                   LANGGRAPH WORKFLOW                  │
                    └──────────────────────────────────────────────────────┘

     [START]
        │
        ▼
┌───────────────┐     yes     ┌───────────────┐     ┌───────────────┐
│ plan_query    │────────────►│ retrieve_rag  │────►│ retrieve_kg   │
│ (Query       │             │ (Qdrant)      │     │ (Neo4j)       │
│  Planner)    │             └───────────────┘     └───────┬───────┘
└───────┬───────┘                                         │
        │ no (out of scope)                               ▼
        │                                         ┌───────────────┐
        │                                         │ rerank        │
        │                                         └───────┬───────┘
        │                                                 │
        │                                                 ▼
        │                                         ┌───────────────┐
        │                                         │ synthesize    │
        │                                         └───────┬───────┘
        │                                                 │
        │                                                 ▼
        │                                         ┌───────────────┐
        │                                         │ self_reflect  │
        │                                         └───────┬───────┘
        │                                                 │
        └─────────────────────────────────────────────────┴──► [END]
```

---

## 6. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA FLOW                                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘

TRANSCRIPTS (.txt)                    KNOWLEDGE GRAPH (Neo4j)
        │                                      ▲
        │ load_transcripts                     │ writer.merge_nodes
        ▼                                      │ writer.merge_relationships
   LangChain Docs                              │
        │                                      │
        │ chunk_documents                      │
        ▼                                      │
   Chunks (metadata: episode_id, source_path)  │
        │                                      │
        ├──────────────────────────────────────┘
        │ extractor (LLM) → concepts, relationships, quotes
        │
        │ ingest_qdrant
        ▼
   QDRANT (vectors + metadata)
        │
        │ hybrid_retriever.retrieve()
        ▼
   Retrieved chunks + KG context
        │
        │ agent synthesizes
        ▼
   Answer + sources
```

---

## 7. Knowledge Graph Schema (Neo4j)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           NEO4J SCHEMA                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

NODES:
  (:Concept {id, name, type, description, workspace_id, episode_ids, source_paths, ...})
  (:Person {id, name, ...})
  (:Place {id, name, ...})
  (:Organization {id, name, ...})
  (:Event {id, name, ...})
  (:Quote {id, text, speaker, timestamp, episode_id, ...})

RELATIONSHIPS:
  (:Concept)-[:CAUSES {confidence}]->(:Concept)
  (:Concept)-[:INFLUENCES {confidence}]->(:Concept)
  (:Concept)-[:OPTIMIZES {confidence}]->(:Concept)
  (:Concept)-[:ENABLES {confidence}]->(:Concept)
  (:Concept)-[:REDUCES {confidence}]->(:Concept)
  (:Concept)-[:LEADS_TO {confidence}]->(:Concept)
  (:Concept)-[:REQUIRES {confidence}]->(:Concept)
  (:Concept)-[:RELATES_TO {confidence}]->(:Concept)
  (:Concept)-[:IS_PART_OF {confidence}]->(:Concept)
  (:Concept)-[:CROSS_EPISODE {episodes, co_occurrences}]->(:Concept)

  (:Person)-[:SAID]->(:Quote)
  (:Quote)-[:ABOUT]->(:Concept)
```

---

## 8. Workspace Isolation

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           WORKSPACE ISOLATION                                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  • Every request carries X-Workspace-Id (or default)
  • Neo4j: workspace_id property on all nodes/relationships
  • Qdrant: collection = "{workspace_id}_chunks"
  • Transcripts: data/workspaces/{workspace_id}/transcripts/
  • Sessions: session_db filtered by workspace_id
  • Reasoner pool: one KGReasoner per workspace (reused)
```

---

## 9. File Structure

```
ontology_production_v1/
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/         # query, ingestion, graph, scripts, workspace, sessions
│   │   ├── core/               # reasoner_pool, workspace
│   │   ├── database/           # job_db, session_db
│   │   └── services/           # ingestion_service
│   └── requirements.txt
├── core_engine/                # Business logic
│   ├── chunking/               # chunker.py
│   ├── embeddings/             # ingest_qdrant.py
│   ├── ingestion/              # loader.py
│   ├── kg/                     # extractor, neo4j_client, normalizer, writer, cross_episode
│   ├── reasoning/              # agent, hybrid_retriever, langgraph_*, reasoning.py
│   ├── script_generation/      # script_generator, narrative_builder, etc.
│   └── metrics/                # cost_tracker, performance_tracker
├── frontend/                   # React + Vite
│   └── src/
│       ├── pages/              # Chat, Dashboard, Upload, Explore, Scripts
│       ├── components/         # ChatMessage, StyleSelector, ToneSelector
│       └── services/api.js     # API client
├── data/
│   └── workspaces/{id}/transcripts/
├── docs/                       # Architecture, Documentation
└── docker-compose.yml          # Qdrant service
```

---

## 10. External Dependencies

| Service   | Purpose                          | Env vars                              |
|----------|-----------------------------------|---------------------------------------|
| Neo4j    | Knowledge graph storage           | NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD |
| Qdrant   | Vector embeddings (semantic search)| QDRANT_URL, QDRANT_API_KEY           |
| OpenAI   | LLM (GPT-4) + embeddings          | OPENAI_API_KEY                        |

---

*Last updated: February 2025*
