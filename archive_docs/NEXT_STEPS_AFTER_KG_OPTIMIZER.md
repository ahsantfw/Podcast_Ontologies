# Next Steps After Query Planner, Reranker & KG Optimizer

## ✅ Completed (Phase 1 & 2)

1. ✅ **Intelligent Query Planner** - Context analysis, domain relevance, complexity assessment, query decomposition
2. ✅ **Reranking (RRF, MMR, Hybrid)** - Configurable reranking strategies
3. ✅ **KG Query Optimizer** - Entity linking, multi-hop queries, cross-episode queries

---

## 🎯 Next Steps (Phase 2 & 3)

### 4. Query Expansion 🔄 **NEXT PRIORITY**
**Priority**: 🟡 **MEDIUM** (Improves coverage)

**Goal**: Generate query variations to improve retrieval coverage

**Why**: Single query might miss relevant results. Variations increase recall.

**Example**:
- Original: "What is meditation?"
- Variations:
  - "What is the practice of meditation?"
  - "How is meditation defined?"
  - "What does meditation involve?"
  - "Tell me about meditation"

**Benefits**:
- **Broader Coverage**: Finds results that original query missed
- **Better Recall**: Increases chance of finding relevant information
- **Handles Synonyms**: Finds results using different terminology

**Implementation**:
- Create `core_engine/reasoning/query_expander.py`
- Use LLM to generate variations (synonyms, rephrasing, questions)
- Multi-query retrieval (search with all variations)
- Result merging and deduplication

**When to Use**:
- Only for moderate/complex queries (per query plan)
- Not for simple queries (performance - avoid unnecessary overhead)
- Controlled by query planner's `retrieval_strategy.rag_expansion` flag

**Files to Create**:
- `core_engine/reasoning/query_expander.py`

**Files to Modify**:
- `core_engine/reasoning/langgraph_nodes.py` (retrieve_rag_node)

**Expected Impact**:
- **Coverage**: +10-20% more relevant results found
- **Latency**: +100-200ms (acceptable for complex queries)
- **Quality**: Better recall, more complete answers

---

### 5. Enhanced Ground Truth 🔄 **AFTER QUERY EXPANSION**
**Priority**: 🟡 **MEDIUM** (Improves UX)

**Goal**: Better source extraction, timestamps, speaker resolution

**Why**: Users want to see exactly where information came from (episode, timestamp, speaker).

**Current Issues**:
- Episode names not formatted consistently
- Timestamps missing or not formatted
- Speaker names not resolved
- Source confidence scores missing

**Improvements**:
1. **Better Episode Name Formatting**
   - Format: "Episode: 001_PHIL_JACKSON" → "Phil Jackson (Episode 001)"
   - Extract episode metadata (title, date if available)

2. **Timestamp Extraction and Formatting**
   - Extract timestamps from RAG results
   - Format: "00:15:30" → "15:30"
   - Link timestamps to sources

3. **Speaker Resolution**
   - Map speaker IDs to names
   - Extract speaker from KG relationships
   - Display: "Phil Jackson said..."

4. **Source Confidence Scores**
   - Calculate confidence based on:
     - Relevance score
     - Number of sources mentioning it
     - KG relationship strength
   - Display confidence in UI

**Files to Modify**:
- `core_engine/reasoning/agent.py` (`_extract_sources`)

**Expected Impact**:
- **UX**: Better source attribution
- **Trust**: Users can verify information
- **Navigation**: Users can jump to specific timestamps

---

## 📊 Implementation Order

### Week 1: Query Expansion
**Day 1-2**: Core Implementation
- Create `query_expander.py`
- Implement query variation generation
- Test with real queries

**Day 3-4**: Integration
- Wire into LangGraph `retrieve_rag_node`
- Respect query plan's `rag_expansion` flag
- Test end-to-end

**Day 5**: Testing & Refinement
- Measure coverage improvements
- Tune variation count
- Optimize performance

---

### Week 2: Enhanced Ground Truth
**Day 1-2**: Source Extraction
- Improve episode name formatting
- Extract and format timestamps
- Resolve speaker names

**Day 3-4**: Confidence Scores
- Calculate source confidence
- Display in UI
- Test with various queries

**Day 5**: Testing & Documentation
- Verify source accuracy
- Test timestamp links
- Document changes

---

## 🎯 Success Criteria

### After Query Expansion:
- ✅ Coverage: +10-20% more results found
- ✅ Recall: Better retrieval for complex queries
- ✅ Latency: < 500ms overhead for complex queries

### After Enhanced Ground Truth:
- ✅ Sources: Properly formatted episode names
- ✅ Timestamps: Extracted and formatted correctly
- ✅ Speakers: Resolved and displayed
- ✅ Confidence: Scores calculated and shown

---

## 📈 Expected Overall Impact

### Current State:
- **KG Utilization**: ~70% (after optimizer)
- **Coverage**: Good for simple queries, moderate for complex
- **Source Quality**: Basic (needs improvement)

### After Phase 2 & 3:
- **KG Utilization**: ~70%+ (maintained)
- **Coverage**: +10-20% improvement for complex queries
- **Source Quality**: Excellent (formatted, timestamped, speaker-resolved)

---

## 🚀 Immediate Next Step

**Start with Query Expansion**

**Why First**:
1. **High Impact**: Improves coverage for complex queries
2. **Manageable**: Can be implemented incrementally
3. **Foundation**: Enables better retrieval before improving display

**First Task**: Create `core_engine/reasoning/query_expander.py` with query variation generation.

---

## Files Summary

### To Create:
1. `core_engine/reasoning/query_expander.py` - **NEXT**
2. (Future) `core_engine/reasoning/synthesis_enhancer.py` - Optional

### To Modify:
1. `core_engine/reasoning/langgraph_nodes.py` - Query expansion integration
2. `core_engine/reasoning/agent.py` - Enhanced source extraction

---

## Status

✅ **Phase 1 Complete**: Query Planner + Reranker + KG Optimizer
🔄 **Phase 2 Next**: Query Expansion → Enhanced Ground Truth

**Ready to start**: Query Expansion implementation
