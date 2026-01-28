# Next Steps After Query Planner & Reranker Implementation

## ✅ Completed (Phase 1)

### 1. Intelligent Query Planner ✅
**Status**: ✅ **COMPLETE**
- Context analysis (follow-up detection)
- Domain relevance check (reject irrelevant queries)
- Complexity assessment (simple/moderate/complex)
- Query decomposition (for complex queries)
- Retrieval strategy planning
- Fast paths (greetings, out-of-scope)
- Integrated into LangGraph workflow

**Files**:
- `core_engine/reasoning/intelligent_query_planner.py`
- `core_engine/reasoning/langgraph_nodes.py` (plan_query_node)

---

### 2. Reranking (RRF, MMR, Hybrid) ✅
**Status**: ✅ **COMPLETE**
- Reciprocal Rank Fusion (RRF)
- Maximal Marginal Relevance (MMR)
- Hybrid RRF + MMR
- Configurable via `.env` (`RERANKING_STRATEGY`)
- Integrated into LangGraph workflow

**Files**:
- `core_engine/reasoning/reranker.py`
- `core_engine/reasoning/langgraph_nodes.py` (rerank_node)

---

## 🎯 Next Steps (Phase 2: Enhanced Retrieval)

According to the implementation plan, the next priorities are:

### 3. KG Query Optimizer 🔄 **NEXT**
**Priority**: 🔴 **HIGH** (Improves KG utilization significantly)

**Components**:

#### 3.1 Entity Linking
**Goal**: Map query entities to KG entities (handle aliases, variations)

**Why**: Currently, KG search might miss entities if they're named differently in the query vs KG.

**Example**:
- Query: "What did Phil say about meditation?"
- Current: Searches for exact match "Phil" → might miss "Phil Jackson" or "PJ"
- After: Links "Phil" → "Phil Jackson" → finds all related concepts

**Implementation**:
- Create `core_engine/reasoning/kg_query_optimizer.py`
- Use LLM for fuzzy entity matching
- Handle aliases (Phil → Phil Jackson → PJ)
- Map to KG entity IDs

**Files to Create**:
- `core_engine/reasoning/kg_query_optimizer.py`

**Files to Modify**:
- `core_engine/reasoning/langgraph_nodes.py` (retrieve_kg_node)

---

#### 3.2 Multi-Hop Queries
**Goal**: Traverse relationships 2-3 hops deep

**Why**: Current KG search is single-hop. Complex questions need multi-hop reasoning.

**Example**:
- Query: "What practices lead to better decision-making?"
- Current: Finds practices → stops
- After: Practices → Outcomes → Decision-making (2-3 hops)

**Implementation**:
- Extend Neo4j Cypher queries to traverse relationships
- Variable depth based on query complexity
- Path relevance scoring

**Files to Modify**:
- `core_engine/reasoning/kg_query_optimizer.py`
- `core_engine/reasoning/agent.py` (`_search_knowledge_graph`)

---

#### 3.3 Cross-Episode Queries
**Goal**: Find concepts across multiple episodes

**Why**: Some concepts appear in multiple episodes. Current search might only find one episode.

**Example**:
- Query: "What did multiple speakers say about creativity?"
- Current: Finds one episode
- After: Finds all episodes mentioning creativity, ranks by frequency

**Implementation**:
- Query across all episodes
- Rank by episode frequency
- Episode diversity optimization

**Files to Modify**:
- `core_engine/reasoning/kg_query_optimizer.py`

---

### 4. Query Expansion 🔄 **AFTER KG OPTIMIZER**
**Priority**: 🟡 **MEDIUM** (Improves coverage)

**Goal**: Generate query variations to improve retrieval coverage

**Why**: Single query might miss relevant results. Variations increase recall.

**Example**:
- Original: "What is meditation?"
- Variations:
  - "What is the practice of meditation?"
  - "How is meditation defined?"
  - "What does meditation involve?"

**Implementation**:
- Create `core_engine/reasoning/query_expander.py`
- Use LLM to generate variations (synonyms, rephrasing)
- Multi-query retrieval
- Result merging

**When to Use**:
- Only for moderate/complex queries (per query plan)
- Not for simple queries (performance)

**Files to Create**:
- `core_engine/reasoning/query_expander.py`

**Files to Modify**:
- `core_engine/reasoning/langgraph_nodes.py` (retrieve_rag_node)

---

### 5. Enhanced Ground Truth 🔄 **AFTER QUERY EXPANSION**
**Priority**: 🟡 **MEDIUM** (Improves UX)

**Goal**: Better source extraction, timestamps, speaker resolution

**Why**: Users want to see exactly where information came from (episode, timestamp, speaker).

**Improvements**:
- Better episode name formatting
- Timestamp extraction and formatting
- Speaker resolution
- Source confidence scores

**Files to Modify**:
- `core_engine/reasoning/agent.py` (`_extract_sources`)

---

## 📊 Implementation Order (Recommended)

### Week 1: KG Query Optimizer
**Day 1-2**: Entity Linking
- Implement entity matching
- Handle aliases
- Test with real queries

**Day 3**: Multi-Hop Queries
- Extend Cypher queries
- Test with complex queries

**Day 4**: Cross-Episode Queries
- Query across episodes
- Rank by frequency

**Day 5**: Integration & Testing
- Wire into LangGraph
- End-to-end testing
- Performance measurement

---

### Week 2: Query Expansion
**Day 1-2**: Core Implementation
- Create query expander
- Generate variations
- Multi-query retrieval

**Day 3-4**: Integration
- Wire into RAG retrieval
- Test coverage improvements

**Day 5**: Testing & Refinement

---

### Week 3: Enhanced Ground Truth
**Day 1-2**: Source Extraction
- Better episode formatting
- Timestamp extraction
- Speaker resolution

**Day 3-4**: Testing
- Verify source accuracy
- Test with various queries

**Day 5**: Documentation

---

## 🎯 Success Criteria

### After KG Query Optimizer:
- ✅ KG returns results for complex queries (currently often 0)
- ✅ Multi-hop relationships traversed correctly
- ✅ Cross-episode concepts found
- ✅ KG utilization: 20% → 70%+

### After Query Expansion:
- ✅ Broader retrieval coverage
- ✅ More relevant results found
- ✅ Recall improved

### After Enhanced Ground Truth:
- ✅ Sources properly displayed
- ✅ Timestamps accurate
- ✅ Speaker names resolved

---

## 📈 Expected Impact

### Current State:
- **KG Utilization**: ~20% (often returns 0 results)
- **Complex Query Success**: ~60%
- **KG Results**: Often empty for complex queries

### After Phase 2:
- **KG Utilization**: ~70%+ (results for most queries)
- **Complex Query Success**: ~85%+
- **KG Results**: Relevant multi-hop, cross-episode results

---

## 🚀 Immediate Next Step

**Start with KG Query Optimizer - Entity Linking**

**Why First**:
1. **Highest Impact**: KG currently underutilized (often 0 results)
2. **Foundation**: Entity linking enables multi-hop and cross-episode
3. **Manageable**: Can be implemented incrementally

**First Task**: Create `kg_query_optimizer.py` with entity linking functionality.

---

## Files Summary

### To Create:
1. `core_engine/reasoning/kg_query_optimizer.py` - **NEXT**
2. `core_engine/reasoning/query_expander.py` - After KG optimizer

### To Modify:
1. `core_engine/reasoning/langgraph_nodes.py` - Use KG optimizer
2. `core_engine/reasoning/agent.py` - Enhanced source extraction
3. `core_engine/reasoning/hybrid_retriever.py` - Query expansion integration

---

## Notes

- **Don't skip ahead**: KG Query Optimizer is foundational for multi-hop and cross-episode
- **Test incrementally**: Implement one component at a time
- **Measure impact**: Track KG utilization before/after
- **Performance**: Keep fast paths for simple queries

---

## Status

✅ **Phase 1 Complete**: Query Planner + Reranker
🔄 **Phase 2 Next**: KG Query Optimizer → Query Expansion → Enhanced Ground Truth

**Ready to start**: KG Query Optimizer implementation
