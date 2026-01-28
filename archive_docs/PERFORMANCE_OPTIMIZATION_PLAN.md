# Performance Optimization Plan - Query Response Time

## Problem Statement

When querying the chatbot, responses take longer than expected. The system searches both RAG (Qdrant) and KG (Neo4j), and the overall response time is slower than desired.

---

## Current Query Flow Analysis

### Step-by-Step Flow:

```
1. User sends query → API endpoint
   ↓
2. Create NEW KGReasoner instance (EXPENSIVE!)
   - Initialize Neo4j client
   - Initialize HybridRetriever (Qdrant + OpenAI clients)
   - Initialize QueryGenerator
   - Initialize MultiHopReasoner
   - Initialize Agent
   - Initialize SessionManager
   ↓
3. Get/Create session (DB lookup if not in memory)
   ↓
4. Agent.run() - Intent Classification
   - LLM Call #1: Classify intent
   ↓
5. If knowledge_query:
   a. Extract entities (CPU)
   b. Resolve pronouns (CPU)
   ↓
6. RAG Search (SEQUENTIAL)
   - Generate embedding (OpenAI API call)
   - Search Qdrant (Network call)
   ↓
7. KG Search (SEQUENTIAL - waits for RAG)
   - Execute Neo4j Cypher query (Network call)
   - Multiple queries for different search terms (up to 3)
   ↓
8. Entity filtering/validation (CPU)
   ↓
9. Answer Synthesis
   - LLM Call #2: Generate answer
   ↓
10. Save session to DB
   ↓
11. Close reasoner (cleanup)
   ↓
12. Return response
```

---

## Identified Bottlenecks

### 🔴 CRITICAL (Biggest Impact)

#### 1. **New KGReasoner Created Per Request**
**Location**: `backend/app/api/routes/query.py` lines 49-55

**Problem**:
```python
# EVERY request creates a new reasoner!
reasoner = create_reasoner(
    workspace_id=workspace_id,
    use_llm=True,
    use_hybrid=True
)
```

**Impact**:
- Initializes Neo4j connection
- Initializes Qdrant client
- Initializes OpenAI client
- Creates all components from scratch
- **Estimated time**: 200-500ms per request

**Solution**: Use connection pooling or singleton pattern

---

#### 2. **Sequential RAG + KG Searches**
**Location**: `core_engine/reasoning/agent.py` lines 1218-1234

**Problem**:
```python
# RAG Search (waits for completion)
rag_results = self.hybrid_retriever.retrieve(...)

# THEN KG Search (waits for RAG to finish)
kg_results = self._search_knowledge_graph(...)
```

**Impact**:
- RAG search: ~300-800ms (embedding + Qdrant)
- KG search: ~200-500ms (Neo4j queries)
- **Total sequential**: ~500-1300ms
- **Could be parallel**: ~300-800ms (max of both)

**Solution**: Run RAG and KG searches in parallel

---

### 🟡 HIGH PRIORITY

#### 3. **Multiple LLM Calls Per Query**
**Location**: Multiple locations

**Problem**:
- Intent Classification: 1 LLM call (~200-500ms)
- Answer Synthesis: 1 LLM call (~500-2000ms)
- **Total**: ~700-2500ms

**Impact**: LLM calls are the slowest operations

**Solution**: 
- Cache intent classification for similar queries
- Optimize prompt length
- Use faster models where possible

---

#### 4. **Embedding Generation Per Query**
**Location**: `core_engine/reasoning/hybrid_retriever.py` lines 176-180

**Problem**:
```python
# Creates embedding for EVERY query
response = self.openai_client.embeddings.create(
    model=self.embed_model,
    input=[query],
)
```

**Impact**:
- Embedding API call: ~100-300ms per query
- No caching for similar queries

**Solution**: Cache embeddings for similar queries

---

#### 5. **Multiple KG Queries for Search Terms**
**Location**: `core_engine/reasoning/agent.py` lines 1354-1360

**Problem**:
```python
# Loops through up to 3 search terms
for term in search_terms[:3]:
    result = self.neo4j_client.execute_read(cypher, ...)
    results.extend(result)
```

**Impact**:
- 3 sequential Neo4j queries: ~300-900ms
- Could be optimized with single query

**Solution**: Combine into single optimized query

---

### 🟢 MEDIUM PRIORITY

#### 6. **Session Loading from DB**
**Location**: `core_engine/reasoning/session_manager.py` lines 260-323

**Problem**:
- If session not in memory, loads from SQLite
- Parses JSON messages
- **Estimated**: 50-200ms

**Solution**: Better caching, async loading

---

#### 7. **No Result Caching**
**Problem**:
- Same queries hit RAG/KG every time
- No caching layer

**Solution**: Add Redis or in-memory cache

---

#### 8. **Large Prompt Context**
**Location**: `core_engine/reasoning/agent.py` `_synthesize_answer()`

**Problem**:
- Sends full conversation history (last 5 messages)
- Large RAG/KG context
- **Impact**: Slower LLM processing, higher costs

**Solution**: Optimize context size, use summarization

---

## Performance Improvement Plan

### Phase 1: Quick Wins (High Impact, Low Effort)

#### 1.1 Parallelize RAG + KG Searches
**Priority**: 🔴 CRITICAL
**Effort**: Medium
**Impact**: 30-50% faster (500-1300ms → 300-800ms)

**Implementation**:
- Use `asyncio` or `concurrent.futures`
- Run RAG and KG searches simultaneously
- Wait for both to complete before synthesis

**Files to Modify**:
- `core_engine/reasoning/agent.py` - `_handle_knowledge_query()`

**Code Change**:
```python
# Before (Sequential):
rag_results = self.hybrid_retriever.retrieve(...)
kg_results = self._search_knowledge_graph(...)

# After (Parallel):
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor() as executor:
    rag_future = executor.submit(self.hybrid_retriever.retrieve, ...)
    kg_future = executor.submit(self._search_knowledge_graph, ...)
    rag_results = rag_future.result()
    kg_results = kg_future.result()
```

---

#### 1.2 Connection Pooling / Singleton Pattern
**Priority**: 🔴 CRITICAL
**Effort**: High
**Impact**: 20-40% faster (200-500ms saved per request)

**Implementation**:
- Create reasoner pool per workspace
- Reuse reasoner instances
- Clean up idle reasoners after timeout

**Files to Modify**:
- `backend/app/api/routes/query.py`
- Create: `backend/app/core/reasoner_pool.py`

**Approach**:
```python
# ReasonerPool class
class ReasonerPool:
    def __init__(self):
        self.pools = {}  # workspace_id -> reasoner
    
    def get_reasoner(self, workspace_id):
        if workspace_id not in self.pools:
            self.pools[workspace_id] = create_reasoner(...)
        return self.pools[workspace_id]
```

---

#### 1.3 Optimize KG Search Query
**Priority**: 🟡 HIGH
**Effort**: Low
**Impact**: 20-30% faster KG search (300-900ms → 200-600ms)

**Implementation**:
- Combine multiple search terms into single query
- Use UNION or OR conditions
- Optimize Cypher query

**Files to Modify**:
- `core_engine/reasoning/agent.py` - `_search_knowledge_graph()`

---

### Phase 2: Medium-Term Improvements

#### 2.1 Embedding Caching
**Priority**: 🟡 HIGH
**Effort**: Medium
**Impact**: 10-20% faster (100-300ms saved)

**Implementation**:
- Cache embeddings for similar queries
- Use semantic similarity to find cached embeddings
- TTL: 24 hours

**Files to Create**:
- `core_engine/reasoning/embedding_cache.py`

---

#### 2.2 Result Caching
**Priority**: 🟡 HIGH
**Effort**: High
**Impact**: 50-80% faster for repeated queries

**Implementation**:
- Cache RAG + KG results
- Key: query hash + workspace_id
- TTL: 1 hour
- Invalidate on data updates

**Files to Create**:
- `core_engine/reasoning/result_cache.py`

---

#### 2.3 Intent Classification Caching
**Priority**: 🟢 MEDIUM
**Effort**: Low
**Impact**: 5-10% faster (200-500ms saved for similar queries)

**Implementation**:
- Cache intent classification results
- Key: query hash
- TTL: 1 hour

---

### Phase 3: Advanced Optimizations

#### 3.1 Async/Await Pattern
**Priority**: 🟢 MEDIUM
**Effort**: High
**Impact**: Better concurrency, 10-20% faster

**Implementation**:
- Convert to async/await
- Use async Neo4j client
- Use async Qdrant client
- Use async OpenAI client

**Files to Modify**:
- All query-related files

---

#### 3.2 Prompt Optimization
**Priority**: 🟢 MEDIUM
**Effort**: Medium
**Impact**: 10-15% faster LLM calls, lower costs

**Implementation**:
- Reduce prompt size
- Use summarization for long context
- Optimize system prompts

---

#### 3.3 Streaming Responses
**Priority**: 🟢 MEDIUM
**Effort**: High
**Impact**: Perceived performance (feels faster)

**Implementation**:
- Stream LLM responses
- Show partial results as they arrive
- Better UX

---

## Expected Performance Improvements

### Current Performance (Estimated):
- **Total Time**: 2-5 seconds per query
- Breakdown:
  - Reasoner creation: 200-500ms
  - Intent classification: 200-500ms
  - RAG search: 300-800ms
  - KG search: 200-500ms (sequential)
  - Synthesis: 500-2000ms
  - Other: 100-200ms

### After Phase 1 (Quick Wins):
- **Total Time**: 1.2-3 seconds per query
- **Improvement**: 40-50% faster

### After Phase 2 (Medium-Term):
- **Total Time**: 0.8-2 seconds per query
- **Improvement**: 60-70% faster

### After Phase 3 (Advanced):
- **Total Time**: 0.5-1.5 seconds per query
- **Improvement**: 70-80% faster

---

## Implementation Priority

### Must Do (Phase 1):
1. ✅ Parallelize RAG + KG searches
2. ✅ Connection pooling / Singleton
3. ✅ Optimize KG search query

### Should Do (Phase 2):
4. ✅ Embedding caching
5. ✅ Result caching
6. ✅ Intent classification caching

### Nice to Have (Phase 3):
7. ✅ Async/await pattern
8. ✅ Prompt optimization
9. ✅ Streaming responses

---

## Measurement Plan

### Before Optimization:
- Measure current response times
- Log timing for each step
- Identify actual bottlenecks

### After Each Phase:
- Measure improvements
- Compare before/after
- Validate improvements

### Metrics to Track:
- Total query time
- RAG search time
- KG search time
- LLM call times
- Reasoner creation time
- Session loading time

---

## Risk Assessment

### Low Risk:
- Parallelizing searches
- Optimizing queries
- Caching embeddings

### Medium Risk:
- Connection pooling (memory usage)
- Result caching (stale data)

### High Risk:
- Async/await conversion (breaking changes)

---

## Testing Strategy

1. **Load Testing**: Test with multiple concurrent requests
2. **Performance Testing**: Measure before/after times
3. **Functional Testing**: Ensure correctness after optimizations
4. **Stress Testing**: Test under high load

---

## Success Criteria

- **Target**: < 1 second response time for 80% of queries
- **Current**: 2-5 seconds
- **Goal**: 50-80% improvement

---

## Next Steps

1. ✅ Create plan (THIS DOCUMENT)
2. ⏳ Implement Phase 1 optimizations
3. ⏳ Measure improvements
4. ⏳ Implement Phase 2 optimizations
5. ⏳ Measure improvements
6. ⏳ Consider Phase 3 if needed

---

## Files That Need Changes

### Phase 1:
1. `backend/app/api/routes/query.py` - Connection pooling
2. `core_engine/reasoning/agent.py` - Parallelize searches
3. `core_engine/reasoning/agent.py` - Optimize KG query

### Phase 2:
4. `core_engine/reasoning/embedding_cache.py` - NEW
5. `core_engine/reasoning/result_cache.py` - NEW
6. `core_engine/reasoning/agent.py` - Add caching

### Phase 3:
7. Multiple files - Async conversion
8. `core_engine/reasoning/agent.py` - Prompt optimization
9. `backend/app/api/routes/query.py` - Streaming

---

## Notes

- **Don't optimize prematurely** - Measure first
- **Test thoroughly** - Optimizations can introduce bugs
- **Monitor** - Track performance metrics
- **Iterate** - Start with quick wins, then optimize further
