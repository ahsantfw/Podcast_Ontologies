# Performance and KG Issues Analysis

## Issues Identified

### 1. Font Reverted ✅
- Changed font back from Times New Roman to default system font

### 2. Response Time Issues

#### Potential Causes:

**A. Intent Classification Delay**
- Every query goes through `_classify_intent_llm()` which is a full LLM call
- This happens BEFORE any search, adding ~1-2 seconds delay
- Location: `reasoning.py:322`

**B. Parallel Search Blocking**
- RAG + KG searches run in parallel but `future.result()` blocks until BOTH complete
- If KG is slow, it delays the entire response
- Location: `reasoning.py:431-437`

**C. KG Search Performance**
- KG search uses `OPTIONAL MATCH` which can be slow on large graphs
- No timeout on Neo4j queries
- Location: `agent.py:1386-1406`

**D. Streaming Synthesis Delay**
- Answer synthesis waits for ALL search results before starting to stream
- No progressive streaming (search → stream immediately)
- Location: `reasoning.py:444-457`

### 3. KG Not Working Correctly

#### Potential Issues:

**A. KG Search May Be Failing Silently**
- Errors are caught and logged as warnings, but search returns empty list
- No indication to user that KG search failed
- Location: `agent.py:1420-1422`

**B. KG Results May Not Be Used**
- KG results are passed to synthesis but may be empty
- No validation that KG actually returned useful data
- Location: `reasoning.py:450`

**C. Workspace ID Mismatch**
- KG search filters by `workspace_id` - if wrong workspace, returns nothing
- No logging of workspace_id used in search
- Location: `agent.py:1388`

**D. Search Terms Too Restrictive**
- Only searches for terms > 2 chars and filters stop words
- May miss important single-word queries
- Location: `agent.py:1372-1380`

## Recommendations

### Immediate Fixes:

1. **Add Timeout to KG Search**
   ```python
   # Add timeout to Neo4j query execution
   results = self.neo4j_client.execute_read(
       cypher, 
       {"workspace_id": self.workspace_id, "search_terms": search_terms},
       timeout=5.0  # 5 second timeout
   )
   ```

2. **Better Error Handling**
   - Log KG search failures more prominently
   - Return partial results if one search fails
   - Don't block on KG if RAG succeeds

3. **Progressive Streaming**
   - Start streaming as soon as RAG results arrive
   - Add KG results to context mid-stream if they arrive later
   - Don't wait for both searches to complete

4. **Add Performance Logging**
   - Log time taken for each step (intent classification, RAG, KG, synthesis)
   - Identify bottlenecks

5. **KG Search Validation**
   - Log workspace_id being searched
   - Log number of nodes in KG for that workspace
   - Validate Neo4j connection before search

6. **Optimize Intent Classification**
   - Cache intent for similar queries
   - Use faster model for intent classification
   - Skip classification for obvious queries (greetings, etc.)

### Code Changes Needed:

1. Add timeout to Neo4j queries
2. Add performance timing logs
3. Make KG search non-blocking (don't wait if slow)
4. Add KG connection health check
5. Improve error messages when KG fails
