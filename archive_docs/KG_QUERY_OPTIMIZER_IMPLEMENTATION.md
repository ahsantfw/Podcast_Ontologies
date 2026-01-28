# KG Query Optimizer Implementation

## ✅ Implementation Complete

### What Was Implemented

1. **KG Query Optimizer** (`core_engine/reasoning/kg_query_optimizer.py`)
   - Entity Linking: Maps query entities to KG entities (handles aliases)
   - Multi-Hop Queries: Traverses relationships 2-3 hops deep
   - Cross-Episode Queries: Finds concepts across multiple episodes
   - Complex Queries: Combines entity linking + multi-hop

2. **Integration into LangGraph** (`core_engine/reasoning/langgraph_nodes.py`)
   - Updated `retrieve_kg_node()` to use KG Query Optimizer
   - Falls back to basic search if optimizer unavailable
   - Respects query plan's `kg_query_type` setting

3. **Before/After Test** (`test_kg_optimizer_before_after.py`)
   - Comprehensive test suite covering all query types
   - Measures accuracy, latency, and improvements
   - Saves results to JSON for analysis

---

## Features

### 1. Entity Linking

**Problem**: Query might say "Phil" but KG has "Phil Jackson" or "PJ"

**Solution**:
- Extracts entities from query (capitalized words, quoted strings)
- Maps aliases (Phil → Phil Jackson, PJ)
- Uses LLM for fuzzy matching (if available)
- Searches KG with both original and linked entities

**Example**:
```python
query = "What did Phil say about meditation?"
# Extracts: ["Phil"]
# Links to: ["Phil Jackson", "PJ"]
# Searches with: ["Phil", "Phil Jackson", "PJ", "meditation"]
```

---

### 2. Multi-Hop Queries

**Problem**: Current search is single-hop. Complex questions need 2-3 hops.

**Solution**:
- Detects relationship types from query ("lead to" → LEADS_TO, "optimize" → OPTIMIZES)
- Traverses relationships 1-3 hops deep
- Returns paths with relationship chains
- Orders by path length (shorter = more relevant)

**Example**:
```python
query = "What practices lead to better decision-making?"
# Finds: Practices → OPTIMIZES → Outcomes → Decision-making (2-3 hops)
# Returns: Path with relationships and concepts
```

---

### 3. Cross-Episode Queries

**Problem**: Concepts appear in multiple episodes. Current search might only find one.

**Solution**:
- Finds concepts with `episode_ids.length >= 2`
- Ranks by episode count (more episodes = more important)
- Searches across all episodes for matching concepts

**Example**:
```python
query = "What concepts appear in multiple episodes?"
# Finds: Concepts with episode_ids.length >= 2
# Returns: Ranked by episode_count DESC
```

---

### 4. Complex Queries

**Problem**: Some queries need both entity linking AND multi-hop.

**Solution**:
- Combines entity linking + multi-hop search
- Deduplicates results
- Returns top results from both methods

---

## Integration

### LangGraph Workflow

The optimizer is integrated into `retrieve_kg_node()`:

```python
# Before (basic search):
results = agent._search_knowledge_graph(query)

# After (optimized search):
optimizer = KGQueryOptimizer(...)
results = optimizer.search(query, query_type=kg_query_type)
```

**Fallback**: If optimizer fails or unavailable, falls back to basic search.

---

## Query Type Detection

The optimizer auto-detects query type:

- **"multiple episodes"** → `cross_episode`
- **"lead to", "relate to", "optimize"** → `multi_hop`
- **"did", "said", "recommend"** → `entity_linking`
- **Default** → `entity_centric`

---

## Performance

### Expected Improvements

- **KG Utilization**: 20% → 70%+ (queries that return results)
- **Entity Linking**: Finds entities that were missed before
- **Multi-Hop**: Answers complex relationship questions
- **Cross-Episode**: Finds concepts across episodes

### Latency

- **Entity Linking**: +50-100ms (LLM call if used)
- **Multi-Hop**: +100-200ms (more complex Cypher)
- **Cross-Episode**: +50-100ms (episode counting)
- **Overall**: Acceptable trade-off for accuracy improvement

---

## Testing

### Test File: `test_kg_optimizer_before_after.py`

**Usage**:
```bash
# Run before test (baseline)
python3 test_kg_optimizer_before_after.py --before-only

# Implement optimizer, then run after test
python3 test_kg_optimizer_before_after.py --after-only

# Run both (full comparison)
python3 test_kg_optimizer_before_after.py
```

**Test Queries**:
1. Entity Linking: "What did Phil say about meditation?"
2. Multi-Hop: "What practices lead to better decision-making?"
3. Cross-Episode: "What concepts appear in multiple episodes?"
4. Complex: "What practices improve mental health outcomes?"

**Metrics**:
- Latency (ms)
- KG Results Count
- Coverage (queries with results)
- Query-by-query comparison

---

## Files Modified

1. **`core_engine/reasoning/kg_query_optimizer.py`** (NEW)
   - Main optimizer implementation

2. **`core_engine/reasoning/langgraph_nodes.py`**
   - Updated `retrieve_kg_node()` to use optimizer

3. **`test_kg_optimizer_before_after.py`** (NEW)
   - Comprehensive before/after test

---

## Next Steps

1. **Run Before Test**: Establish baseline
   ```bash
   python3 test_kg_optimizer_before_after.py --before-only
   ```

2. **Test Optimizer**: Verify it works
   - Test entity linking
   - Test multi-hop queries
   - Test cross-episode queries

3. **Run After Test**: Measure improvements
   ```bash
   python3 test_kg_optimizer_before_after.py --after-only
   ```

4. **Compare Results**: Analyze improvements
   - Check latency impact
   - Verify KG utilization increase
   - Confirm accuracy improvements

---

## Status

✅ **Implementation Complete**
- KG Query Optimizer created
- Integrated into LangGraph workflow
- Test suite created
- Ready for testing

**Next**: Run tests to verify improvements!
