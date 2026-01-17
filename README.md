# Knowledge Graph Pipeline - Production

Complete pipeline for processing transcripts and querying with hybrid RAG + KG.

## Quick Start

```bash
# Cleanup existing data (optional - for fresh start)
python cleanup_database.py --confirm

# Process all transcripts (creates KG + RAG embeddings)
python main.py process --input data/transcripts/

# Query with hybrid RAG + KG
python main.py query

# Or do both at once
python main.py all --input data/transcripts/
```

## Setup

### Step 1: Start Required Services

**Option A: Quick Setup Script (Recommended)**
```bash
./setup_services.sh
```

**Option B: Docker Compose**
```bash
# Use 'docker compose' (newer) or 'docker-compose' (older)
docker compose up -d
# Or if that doesn't work:
docker-compose up -d
```

**Option C: Manual Docker**
```bash
# Neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# Qdrant
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

**Verify services:**
```bash
docker ps  # Should show neo4j and qdrant running
```

### Step 2: Install Dependencies

```bash
pip install neo4j openai python-dotenv qdrant-client langchain langchain-community langchain-openai numpy
```

### Step 3: Configure Environment

Copy `.env.example` to `.env` and update:

```bash
cp .env.example .env
# Edit .env with your settings
```

**Required settings:**
- `NEO4J_PASSWORD` - Your Neo4j password
- `OPENAI_API_KEY` - Your OpenAI API key

See `SETUP.md` for detailed setup instructions.

## Usage

### Process Transcripts

```bash
python main.py process --input data/transcripts/
```

**What it does:**
- Loads all `.txt` files from directory
- Chunks text intelligently
- Extracts knowledge graph (concepts, relationships, quotes)
- Stores in Neo4j
- Creates vector embeddings
- Stores in Qdrant (for RAG)
- Runs cross-episode analysis

### Query Knowledge Graph

```bash
# Hybrid RAG + KG mode (RECOMMENDED)
python main.py query

# Graph-only mode
python main.py query --no-hybrid
```

**How it works:**
1. **RAG (Vector Search)**: Finds relevant text chunks using semantic similarity
2. **KG (Graph Query)**: Queries structured knowledge graph
3. **LLM Synthesis**: Combines both sources into comprehensive answer

### Example Queries

```
💬 Question: What concepts appear in multiple episodes?
💬 Question: who is Avett Brothers
💬 Question: What practices optimize creativity?
💬 Question: What quotes are about meditation?
```

## Structure

```
ontology_production_v1/
├── main.py              # ← SINGLE FILE TO RUN EVERYTHING
├── core_engine/         # Core functionality
│   ├── ingestion/      # Load transcripts
│   ├── chunking/       # Text chunking
│   ├── kg/             # Knowledge graph extraction
│   ├── embeddings/     # Vector embeddings (Qdrant)
│   └── reasoning/      # Query engine (RAG + KG hybrid)
├── data/
│   └── transcripts/    # Your transcript files
└── .env                 # Environment variables
```

## Features

✅ **Hybrid RAG + KG**: Combines vector search with graph queries
✅ **LLM Synthesis**: GPT-4o combines multiple sources
✅ **Cross-Episode Analysis**: Finds recurring concepts across episodes
✅ **No Duplicates**: MERGE operations prevent duplicate entries
✅ **Session Management**: Maintains conversation context
✅ **Production Ready**: Clean, working code

## Troubleshooting

### "Qdrant connection failed"
- Make sure Qdrant is running: `docker ps | grep qdrant`
- Check `QDRANT_URL` in `.env`

### "Neo4j connection failed"
- Make sure Neo4j is running: `docker ps | grep neo4j`
- Check `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in `.env`

### "OPENAI_API_KEY not set"
- Add `OPENAI_API_KEY=your_key` to `.env` file

### Queries return "No results"
- Make sure you've processed transcripts first: `python main.py process`
- Check if data exists in Neo4j/Qdrant

---

**That's it! Use `main.py` for everything.** 🚀
