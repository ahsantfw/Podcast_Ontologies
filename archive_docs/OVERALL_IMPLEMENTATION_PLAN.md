# Overall Implementation Plan: Intelligent Retrieval System

## Executive Summary

**Goal**: Build intelligent, context-aware retrieval system that improves accuracy without degrading performance.

**Key Principles**:
1. ✅ **Intelligence First**: Query Planner understands context, domain, complexity
2. ✅ **Performance Preserved**: Fast paths, caching, no degradation
3. ✅ **Gradual Enhancement**: Improve incrementally, don't break existing
4. ✅ **Future-Ready**: Design for LangGraph migration (but don't require it)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENT RETRIEVAL SYSTEM                          │
└─────────────────────────────────────────────────────────────────────────┘

USER QUERY + SESSION CONTEXT
        ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  INTELLIGENT QUERY PLANNER                                               │
│  • Context Analysis (follow-up? new question?)                          │
│  • Domain Relevance Check (reject math/coding/irrelevant)               │
│  • Complexity Assessment (simple/moderate/complex)                      │
│  • Query Decomposition (if complex)                                     │
│  • Retrieval Strategy Planning                                          │
└─────────────────────────────────────────────────────────────────────────┘
        ↓
    ┌───┴───┐
    │       │
SIMPLE    COMPLEX
PATH      PATH
    │       │
    ↓       ↓
┌─────────┐ ┌──────────────────────────────────────────────┐
│ Fast    │ │ Enhanced Retrieval                           │
│ Answer  │ │ • Multi-query RAG                            │
│ (No     │ │ • Enhanced KG (multi-hop, cross-episode)      │
│ Retrieval│ │ • Query Expansion                           │
│ Needed) │ │ • Iterative (if gaps)                        │
└─────────┘ └──────────────────────────────────────────────┘
        │       │
        └───┬───┘
            ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  RERANKING (RRF)                                                        │
│  • Combine RAG + KG results                                             │
│  • Reciprocal Rank Fusion                                              │
│  • Reorder by relevance                                                │
└─────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  QUALITY ASSESSMENT (Optional)                                          │
│  • Check coverage                                                       │
│  • Identify gaps                                                       │
│  • Trigger corrective retrieval if needed                              │
└─────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  ENHANCED SYNTHESIS                                                     │
│  • Better source extraction                                             │
│  • Citation verification                                                │
│  • Multi-pass refinement                                                │
└─────────────────────────────────────────────────────────────────────────┘
        ↓
    FINAL ANSWER
```

---

## Implementation Phases

### 🎯 PHASE 1: Intelligent Query Planner (Week 1) - **CRITICAL**

**Goal**: Make system intelligent about understanding queries

#### 1.1 Core Query Planner
**File**: `core_engine/reasoning/intelligent_query_planner.py`

**Components**:
- Context Analysis (follow-up detection, entity extraction)
- Domain Relevance Check (reject irrelevant, understand relevance)
- Complexity Assessment (simple/moderate/complex)
- Query Decomposition (break complex queries)
- Retrieval Strategy Planning

**Fast Paths**:
- Greetings → Direct answer (no LLM, no retrieval)
- Out-of-scope patterns → Regex check → Reject (no LLM)
- Simple definitions → Pattern match → Basic retrieval

**Performance**:
- Simple queries: < 50ms overhead (mostly fast paths)
- Complex queries: ~200-300ms (LLM call for planning)
- Caching: Cache plans for similar queries

**Integration**:
- Add to `agent.py` as optional component
- Feature flag: `USE_INTELLIGENT_PLANNER = True`
- Non-breaking: Falls back to current flow if disabled

**Testing**:
- Test greetings (should be instant)
- Test follow-ups (should use context)
- Test out-of-scope (should reject)
- Test complex queries (should decompose)

---

#### 1.2 Integration into Agent
**File**: `core_engine/reasoning/agent.py`

**Changes**:
```python
def _handle_knowledge_query(self, query: str, ...):
    # NEW: Intelligent planning
    plan = self.query_planner.plan(query, conversation_history, session_metadata)
    
    # Fast path: Out of scope
    if not plan.is_relevant:
        return self._handle_out_of_scope(query, plan.rejection_reason)
    
    # Fast path: Simple queries
    if plan.complexity == "simple" and plan.intent == "greeting":
        return self._handle_greeting(query, conversation_history)
    
    # Enhanced retrieval based on plan
    # ... rest of retrieval logic
```

**Backward Compatibility**:
- If planner fails → fall back to current logic
- Feature flag to enable/disable
- Gradual rollout

---

### 🚀 PHASE 2: Enhanced Retrieval (Week 2)

#### 2.1 KG Query Optimizer
**File**: `core_engine/reasoning/kg_query_optimizer.py`

**Components**:
1. **Entity Linking** (Week 2, Day 1)
   - Map query entities to KG entities
   - Handle aliases, variations
   - Use LLM for fuzzy matching

2. **Multi-Hop Queries** (Week 2, Day 2)
   - Traverse relationships 2-3 hops
   - Path relevance scoring
   - Variable depth based on query

3. **Cross-Episode Queries** (Week 2, Day 2)
   - Find concepts across episodes
   - Rank by episode frequency
   - Episode diversity optimization

**Integration**:
- Replace current `_search_knowledge_graph` calls
- Use optimizer based on query plan
- Maintain backward compatibility

---

#### 2.2 Query Expansion
**File**: `core_engine/reasoning/query_expander.py`

**Components**:
- Generate query variations (synonyms, rephrasing)
- Multi-query retrieval
- Result merging

**When to Use**:
- Only for moderate/complex queries (per plan)
- Not for simple queries (performance)

---

#### 2.3 Reranking (RRF)
**File**: `core_engine/reasoning/reranker.py`

**Components**:
- Reciprocal Rank Fusion algorithm
- Combine RAG + KG results
- Reorder by relevance

**Implementation**:
- Simple algorithm, high impact
- No external dependencies
- Fast execution

---

### 🔬 PHASE 3: Quality & Enhancement (Week 3)

#### 3.1 Enhanced Ground Truth
**File**: `core_engine/reasoning/agent.py` (update `_extract_sources`)

**Improvements**:
- Better episode name formatting
- Timestamp extraction and formatting
- Speaker resolution
- Source confidence scores

---

#### 3.2 Synthesis Quality Checks
**File**: `core_engine/reasoning/synthesis_enhancer.py`

**Components**:
- Citation verification
- Hallucination detection
- Multi-pass refinement

**When to Use**:
- Optional for now
- Enable if accuracy issues persist

---

### 🔄 PHASE 4: Advanced Features (Weeks 4+) - **OPTIONAL**

#### 4.1 Iterative Retrieval
**When**: Only if gaps are common after Phase 1-2

**Components**:
- Gap detection
- Refined re-retrieval
- Result merging

---

#### 4.2 Self-Grading
**When**: Only if quality issues persist

**Components**:
- Retrieval quality assessment
- Coverage checking
- Quality scoring

---

#### 4.3 LangGraph Migration (Future)
**When**: After system is stable

**Benefits**:
- Better orchestration
- Easier debugging
- More flexible

**Approach**:
- Design current system with LangGraph in mind
- Migrate gradually
- Don't require LangGraph initially

---

## Detailed Week-by-Week Plan

### Week 1: Intelligent Query Planner

**Day 1-2: Core Implementation**
- [ ] Create `intelligent_query_planner.py`
- [ ] Implement `_analyze_context()` - Follow-up detection
- [ ] Implement `_check_domain_relevance()` - Domain filtering
- [ ] Implement `_assess_complexity()` - Complexity analysis
- [ ] Implement `_decompose_query()` - Query decomposition
- [ ] Implement `_determine_retrieval_strategy()` - Strategy planning
- [ ] Unit tests for each component

**Day 3: Fast Paths**
- [ ] Implement greeting detection (pattern matching)
- [ ] Implement out-of-scope pattern detection (regex)
- [ ] Implement simple query detection
- [ ] Optimize for performance

**Day 4: Integration**
- [ ] Integrate into `agent.py`
- [ ] Add feature flag
- [ ] Update `_handle_knowledge_query`
- [ ] Add fallback logic
- [ ] Integration tests

**Day 5: Testing & Refinement**
- [ ] Test with real queries
- [ ] Measure performance impact
- [ ] Tune prompts
- [ ] Fix issues
- [ ] Documentation

**Deliverables**:
- ✅ Intelligent Query Planner module
- ✅ Integrated into agent
- ✅ Fast paths working
- ✅ Performance maintained

---

### Week 2: Enhanced Retrieval

**Day 1: Entity Linking**
- [ ] Create `kg_query_optimizer.py`
- [ ] Implement entity linking
- [ ] Handle aliases and variations
- [ ] Test with real entities

**Day 2: Multi-Hop & Cross-Episode**
- [ ] Implement multi-hop queries
- [ ] Implement cross-episode queries
- [ ] Test with complex queries

**Day 3: Query Expansion**
- [ ] Create `query_expander.py`
- [ ] Implement query variation generation
- [ ] Integrate multi-query retrieval
- [ ] Test coverage improvements

**Day 4: Reranking**
- [ ] Create `reranker.py`
- [ ] Implement RRF algorithm
- [ ] Integrate into pipeline
- [ ] Test ranking improvements

**Day 5: Integration & Testing**
- [ ] Wire everything together
- [ ] End-to-end testing
- [ ] Performance measurement
- [ ] Bug fixes

**Deliverables**:
- ✅ Enhanced KG querying
- ✅ Query expansion
- ✅ Reranking
- ✅ Integrated system

---

### Week 3: Quality & Polish

**Day 1-2: Enhanced Ground Truth**
- [ ] Improve source extraction
- [ ] Better timestamp handling
- [ ] Speaker resolution
- [ ] Episode name formatting

**Day 3-4: Testing**
- [ ] Test complex queries
- [ ] Test follow-up questions
- [ ] Test out-of-scope rejection
- [ ] Measure accuracy improvements

**Day 5: Documentation & Optimization**
- [ ] Document new components
- [ ] Performance optimization
- [ ] Final testing
- [ ] Prepare for production

**Deliverables**:
- ✅ Enhanced ground truth
- ✅ Tested system
- ✅ Documentation
- ✅ Performance optimized

---

## Performance Targets

### Latency Targets

| Query Type | Current | Target | Overhead |
|------------|---------|--------|----------|
| Simple (greeting) | ~100ms | ~100ms | 0ms (fast path) |
| Simple (definition) | ~500ms | ~550ms | +50ms |
| Moderate | ~800ms | ~1000ms | +200ms |
| Complex | ~1200ms | ~1500ms | +300ms |

**Strategy**: Fast paths minimize overhead for common cases.

---

### Accuracy Targets

| Metric | Current | Target |
|--------|---------|--------|
| Simple Query Success | 90% | 95%+ |
| Complex Query Success | 60% | 85%+ |
| Follow-up Handling | 50% | 90%+ |
| Out-of-Scope Rejection | 70% | 95%+ |
| KG Utilization | 20% | 70%+ |

---

## Risk Management

### Risk 1: Performance Degradation
**Probability**: Medium
**Impact**: High

**Mitigation**:
- Fast paths for simple queries
- Caching for query plans
- Use faster LLM model (`gpt-4o-mini`)
- Measure before/after
- Feature flag to disable if issues

---

### Risk 2: Over-Engineering
**Probability**: Medium
**Impact**: Medium

**Mitigation**:
- Start with simple implementation
- Add complexity only if needed
- Fast paths avoid unnecessary processing
- Clear success criteria

---

### Risk 3: Breaking Current System
**Probability**: Low
**Impact**: High

**Mitigation**:
- Non-breaking integration
- Feature flag
- Gradual rollout
- Fallback to current logic
- Extensive testing

---

### Risk 4: LLM Costs
**Probability**: Medium
**Impact**: Low-Medium

**Mitigation**:
- Use `gpt-4o-mini` (cheaper)
- Cache query plans
- Fast paths avoid LLM calls
- Batch operations where possible

---

## Success Metrics

### Week 1 Success Criteria
- ✅ Query Planner working
- ✅ Fast paths functional
- ✅ No performance degradation
- ✅ Context awareness working
- ✅ Domain filtering working

### Week 2 Success Criteria
- ✅ Enhanced KG queries working
- ✅ Reranking improving results
- ✅ Query expansion increasing coverage
- ✅ Overall accuracy improved

### Week 3 Success Criteria
- ✅ Enhanced ground truth displayed
- ✅ Complex queries handled better
- ✅ Follow-up questions work
- ✅ System stable and performant

---

## Migration Strategy

### Step 1: Add Query Planner (Non-Breaking)
- Add as optional component
- Feature flag: `USE_INTELLIGENT_PLANNER = False`
- Current system continues to work
- Test in parallel

### Step 2: Enable for Testing
- Enable for subset of queries
- Compare accuracy/speed
- Fix issues
- Gradually expand

### Step 3: Full Rollout
- Enable for all queries
- Monitor performance
- Optimize as needed

### Step 4: LangGraph (Future)
- Once stable, consider LangGraph
- Better orchestration
- Easier debugging
- More flexible

---

## Code Structure

```
core_engine/reasoning/
├── intelligent_query_planner.py    # NEW - Week 1
├── kg_query_optimizer.py           # NEW - Week 2
├── query_expander.py                # NEW - Week 2
├── reranker.py                      # NEW - Week 2
├── agent.py                         # MODIFY - Integrate planner
├── hybrid_retriever.py             # MODIFY - Use optimizer
└── reasoning.py                     # MODIFY - Use planner
```

---

## Testing Strategy

### Unit Tests
- Query Planner components
- KG Query Optimizer
- Reranker
- Query Expander

### Integration Tests
- End-to-end query flow
- Context handling
- Domain filtering
- Performance benchmarks

### Real-World Tests
- Complex queries
- Follow-up questions
- Out-of-scope queries
- Performance measurement

---

## Conclusion

This plan provides:
1. ✅ **Intelligent Query Planner** - Context-aware, domain-aware
2. ✅ **Enhanced Retrieval** - Better RAG + KG utilization
3. ✅ **Performance Preserved** - Fast paths, caching
4. ✅ **Gradual Enhancement** - Non-breaking, incremental
5. ✅ **Future-Ready** - LangGraph compatible design

**Next Step**: Start implementing Week 1, Day 1 - Core Query Planner.
