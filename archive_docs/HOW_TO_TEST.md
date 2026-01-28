# How to Test No Results Rejection

## Quick Start

### Step 1: Start Backend
```bash
cd backend
uv run uvicorn app.main:app --reload
```

### Step 2: Start Frontend (Optional)
```bash
cd frontend
npm run dev
```

### Step 3: Test Queries

#### Option A: Via Frontend (Recommended)
1. Open browser: `http://localhost:5173`
2. Open `MANUAL_TEST_QUERIES.md`
3. Copy/paste queries into chat
4. Verify: Should see "I couldn't find information..." when RAG=0, KG=0

#### Option B: Via API Script
```bash
# Install requests if needed
uv pip install requests

# Run test
uv run python test_via_api.py
```

#### Option C: Via curl
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: default" \
  -d '{"question": "What is RAG?", "session_id": "test"}'
```

---

## Test Queries (Top 10)

Test these first - all should be REJECTED with RAG=0, KG=0:

1. What is RAG?
2. Do you know Urdu?
3. What are the issues of society?
4. What is 2+2?
5. What is the weather today?
6. What is happiness?
7. How do I become successful?
8. What can you do?
9. Week 1: Query Expansion
10. Translate hello to Spanish

---

## Expected Results

### For Test Queries:
- **RAG Count**: 0
- **KG Count**: 0
- **Answer**: "I couldn't find information about that in the podcast knowledge base..."
- **Status**: ✅ **REJECTED**

### For Valid Queries:
- **"Hi"**: Should work (greeting, doesn't need results)
- **"Who is Phil Jackson?"**: Should work if RAG/KG has results

---

## Full Test Suite

See `MANUAL_TEST_QUERIES.md` for all 52 test queries.

---

## Troubleshooting

### Backend not running?
```bash
cd backend
uv run uvicorn app.main:app --reload
```

### Frontend not running?
```bash
cd frontend
npm run dev
```

### API test fails?
- Check backend is running on port 8000
- Check `.env` file has correct settings
- Check Neo4j and Qdrant are running

---

## Success Criteria

✅ All 52 test queries should be REJECTED when RAG=0, KG=0
✅ Valid queries (greetings, podcast queries) should work
✅ No false positives (queries with results shouldn't be rejected)
