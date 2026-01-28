# Retrieval System: Problem → Solution Flow Diagram

## Current State Problems

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CURRENT RETRIEVAL SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  USER QUERY: "How do Phil Jackson and Rick Rubin approach creativity?"  │
│                                                                          │
│  ┌──────────────────────┐         ┌──────────────────────┐             │
│  │      RAG PATH        │         │      KG PATH         │             │
│  ├──────────────────────┤         ├──────────────────────┤             │
│  │                      │         │                      │             │
│  │ Query → Embed        │         │ Query → Keywords     │             │
│  │        ↓             │         │        ↓             │             │
│  │ Vector Search        │         │ Keyword Match        │             │
│  │        ↓             │         │        ↓             │             │
│  │ Top-K Results        │         │ 1-Hop Relationships │             │
│  │                      │         │                      │             │
│  └──────────────────────┘         └──────────────────────┘             │
│           │                                  │                          │
│           └──────────────┬──────────────────┘                          │
│                          ↓                                                │
│              Simple Score Fusion                                         │
│                          ↓                                                │
│              Basic Synthesis                                             │
│                          ↓                                                │
│              Answer (Often Incomplete)                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

PROBLEMS IDENTIFIED:
❌ Complex query not decomposed
❌ No query expansion
❌ KG only uses keywords (no semantic)
❌ KG only 1-hop (no multi-hop)
❌ No reranking
❌ No quality check
❌ Missing information
```

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IMPROVED RETRIEVAL SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  USER QUERY: "How do Phil Jackson and Rick Rubin approach creativity?" │
│                          ↓                                               │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │           STEP 1: QUERY PLANNER                             │        │
│  │  • Analyze intent: "multi_entity_comparison"                │        │
│  │  • Extract entities: ["Phil Jackson", "Rick Rubin"]         │        │
│  │  • Decompose: ["Phil Jackson creativity", "Rick Rubin..."]  │        │
│  │  • Plan KG query: multi-hop, entity-centric                 │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                          ↓                                               │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │           STEP 2: QUERY EXPANSION                           │        │
│  │  • Generate variations: ["creative process", "artistic..."]│        │
│  │  • Create multiple query embeddings                         │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                          ↓                                               │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │           STEP 3: ENHANCED RETRIEVAL                        │        │
│  │                                                              │        │
│  │  ┌──────────────────────┐    ┌──────────────────────┐   │        │
│  │  │   ENHANCED RAG        │    │   ENHANCED KG          │   │        │
│  │  ├──────────────────────┤    ├──────────────────────┤   │        │
│  │  │                      │    │                      │   │        │
│  │  │ Multi-query search   │    │ Entity Linking       │   │        │
│  │  │ (expanded queries)   │    │ (map to KG entities) │   │        │
│  │  │        ↓             │    │        ↓             │   │        │
│  │  │ Vector Search        │    │ Multi-Hop Traversal  │   │        │
│  │  │ (multiple queries)   │    │ (2-3 hops deep)      │   │        │
│  │  │        ↓             │    │        ↓             │   │        │
│  │  │ Results from all     │    │ Cross-Episode Query  │   │        │
│  │  │ query variations     │    │ (concepts across eps)│   │        │
│  │  │                      │    │                      │   │        │
│  │  └──────────────────────┘    └──────────────────────┘   │        │
│  │           │                          │                    │        │
│  │           └──────────┬───────────────┘                    │        │
│  │                      ↓                                     │        │
│  │              Multiple Result Lists                         │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                          ↓                                               │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │           STEP 4: RERANKING (RRF)                          │        │
│  │  • Combine RAG + KG results                                 │        │
│  │  • Reciprocal Rank Fusion                                   │        │
│  │  • Reorder by relevance                                     │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                          ↓                                               │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │           STEP 5: QUALITY ASSESSMENT                         │        │
│  │  • Check entity coverage                                     │        │
│  │  • Assess retrieval quality                                  │        │
│  │  • Identify gaps                                             │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                          ↓                                               │
│              ┌───────────┴───────────┐                                 │
│              │                        │                                  │
│         Quality Good?            Quality Poor?                           │
│              │                        │                                  │
│              ↓                        ↓                                  │
│      ┌──────────────┐      ┌──────────────────┐                        │
│      │ Continue     │      │ Corrective RAG   │                        │
│      │ to Synthesis │      │ • Fix query      │                        │
│      │              │      │ • Re-retrieve   │                        │
│      └──────────────┘      └──────────────────┘                        │
│              │                        │                                  │
│              └───────────┬───────────┘                                 │
│                          ↓                                               │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │           STEP 6: ENHANCED SYNTHESIS                         │        │
│  │  • Better source extraction (episode, timestamp, speaker)   │        │
│  │  • Citation verification                                     │        │
│  │  • Multi-pass refinement                                    │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                          ↓                                               │
│              Complete, Accurate Answer with Sources                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Solution Comparison Matrix

| Solution | Impact | Complexity | Time | Priority | Decision |
|----------|--------|------------|------|----------|----------|
| **Query Planner** | 🔴 HIGH | 🟡 Medium | 2-3 days | ⭐⭐⭐ | ✅ DO FIRST |
| **Entity Linking** | 🔴 HIGH | 🟡 Medium | 1-2 days | ⭐⭐⭐ | ✅ DO FIRST |
| **Multi-Hop KG** | 🔴 HIGH | 🟡 Medium | 2-3 days | ⭐⭐⭐ | ✅ DO FIRST |
| **Cross-Episode KG** | 🟠 MED-HIGH | 🟡 Medium | 1-2 days | ⭐⭐ | ✅ DO FIRST |
| **RRF Reranking** | 🔴 HIGH | 🟢 Low | 1 day | ⭐⭐⭐ | ✅ DO FIRST |
| **Query Expansion** | 🟠 MED-HIGH | 🟢 Low | 1-2 days | ⭐⭐ | ✅ DO |
| **Semantic KG** | 🟠 MEDIUM | 🔴 High | 3-4 days | ⭐ | ⚠️ LATER |
| **Iterative Retrieval** | 🟠 MEDIUM | 🟡 Medium | 3-4 days | ⭐ | ⚠️ CONSIDER |
| **Self-Grading** | 🟠 MEDIUM | 🟡 Medium | 2-3 days | ⭐ | ⚠️ CONSIDER |
| **Corrective RAG** | 🟠 MEDIUM | 🔴 High | 3-4 days | ⭐ | ❌ SKIP FOR NOW |
| **Cross-Encoder** | 🟠 MEDIUM | 🔴 High | 2-3 days | ⭐ | ❌ SKIP FOR NOW |
| **Enhanced Ground Truth** | 🟠 MED-HIGH | 🟢 Low | 1-2 days | ⭐⭐ | ✅ DO |

---

## Implementation Order Logic

### Why This Order Makes Sense:

```
1. QUERY PLANNER (Foundation)
   ↓
   Why First? Everything needs to understand the query
   
2. ENTITY LINKING (KG Foundation)
   ↓
   Why Second? KG queries need entities mapped
   
3. MULTI-HOP + CROSS-EPISODE KG (KG Enhancement)
   ↓
   Why Third? Fix KG utilization (biggest gap)
   
4. RRF RERANKING (Result Optimization)
   ↓
   Why Fourth? Need results to rank
   
5. QUERY EXPANSION (RAG Enhancement)
   ↓
   Why Fifth? Broader coverage, but foundation must be solid
   
6. ENHANCED GROUND TRUTH (Synthesis Enhancement)
   ↓
   Why Sixth? Important but can work with current synthesis
   
7. ITERATIVE RETRIEVAL (Optional Enhancement)
   ↓
   Why Seventh? Only if gaps still exist
   
8. SELF-GRADING (Optional Quality)
   ↓
   Why Eighth? Only if quality issues persist
```

---

## Practical Implementation Phases

### 🎯 PHASE 1: Critical Foundation (Weeks 1-2)
**Goal**: Handle complex queries, fix KG utilization

1. Query Planner
2. Entity Linking  
3. Multi-Hop KG Queries
4. Cross-Episode KG Queries
5. RRF Reranking

**Expected Outcome**: 
- ✅ Complex queries work
- ✅ KG properly utilized
- ✅ Better ranking

---

### 🚀 PHASE 2: Enhancement (Week 3)
**Goal**: Improve coverage and quality

6. Query Expansion
7. Enhanced Ground Truth

**Expected Outcome**:
- ✅ Broader retrieval
- ✅ Better source attribution

---

### 🔬 PHASE 3: Advanced (Weeks 4+)
**Goal**: Fine-tune if needed

8. Iterative Retrieval (if gaps exist)
9. Self-Grading (if quality issues)
10. Corrective RAG (only if needed)

**Decision Point**: Evaluate Phase 1-2 results first

---

## Key Decisions Made

### ✅ **DO THESE** (High Value, Manageable)
- Query Planner
- Entity Linking
- Multi-Hop KG
- Cross-Episode KG
- RRF Reranking
- Query Expansion
- Enhanced Ground Truth

**Rationale**: High impact, manageable complexity, addresses core problems

---

### ⚠️ **CONSIDER LATER** (Good Value, Higher Complexity)
- Iterative Retrieval
- Self-Grading
- Synthesis Quality Checks

**Rationale**: Good value but adds complexity. Add only if Phase 1-2 don't solve issues.

---

### ❌ **SKIP FOR NOW** (Overwhelming or Low Priority)
- Semantic KG Search (requires KG embeddings - bigger change)
- Cross-Encoder Reranking (requires additional model)
- Corrective RAG (very complex, only if needed)

**Rationale**: Too complex or requires infrastructure changes. Revisit later if needed.

---

## Success Criteria

### Phase 1 Success Metrics:
- ✅ Complex queries handled correctly
- ✅ KG returns relevant results (not empty)
- ✅ Results ranked better (relevant first)
- ✅ Multi-entity queries work

### Phase 2 Success Metrics:
- ✅ Broader retrieval coverage
- ✅ Sources properly displayed
- ✅ Better answer completeness

### Overall Goal:
- **Complex Query Success**: 60% → 85%+
- **KG Utilization**: 20% → 70%+
- **Answer Completeness**: 60% → 85%+
