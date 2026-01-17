# Backend API Quick Start Guide

## Installation

```bash
cd backend
uv pip install -r requirements.txt
```

## Run Server

```bash
# From ontology_production_v1 directory
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or:
```bash
# From ontology_production_v1 directory
python -m uvicorn backend.app.main:app --reload
```

## API Documentation

Once server is running:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Test Endpoints

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Create Workspace
```bash
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "test-workspace"}'
```

### Query
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: default" \
  -d '{"question": "What practices improve clarity?"}'
```

## Environment Variables

Make sure `.env` file exists with:
```
OPENAI_API_KEY=your_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
QDRANT_URL=http://localhost:6333
WORKSPACE_ID=default
```

