# General Knowledge Block Fix - Post-Retrieval Check

## Problem

**Critical Issue**: The same query ("What are issues of society?") behaves differently in different sessions:
- **Session 1**: RAG=0, KG=0 → Still generates answer (WRONG)
- **Session 2**: RAG=10, KG=10 → Generates proper answer (CORRECT)

**Root Causes**:
1. **Query Planner's LLM-based relevance check is non-deterministic**: Uses `temperature=0.1` but LLM responses can still vary. Sometimes marks general questions as relevant.
2. **Default fallback is TOO PERMISSIVE**: If relevance check fails (exception), it defaults to `is_relevant=True` (dangerous).
3. **No post-retrieval check**: Even if query planner marks as relevant, if retrieval returns RAG=0, KG=0 for a general question → Should be rejected.

---

## Solution: Multi-Layer Protection

### 1. **Stricter Query Planner Default** ✅
**File**: `core_engine/reasoning/intelligent_query_planner.py` → `_check_domain_relevance()`

**Change**: Default to `is_relevant=False` if relevance check fails:
```python
# OLD (DANGEROUS):
return {
    "is_relevant": True,  # ❌ Too permissive
    "reason": "Relevance check failed, defaulting to relevant",
    "confidence": 0.5
}

# NEW (SAFE):
return {
    "is_relevant": False,  # ✅ Safe default
    "reason": "Relevance check failed. I can only answer questions about podcast content.",
    "confidence": 0.0
}
```

**Why**: If we can't determine relevance, safer to reject than accept.

---

### 2. **Post-Retrieval Check After KG Retrieval** ✅
**File**: `core_engine/reasoning/langgraph_nodes.py` → `retrieve_kg_node()`

**Change**: After KG retrieval, check if RAG=0, KG=0 AND query is general knowledge:
```python
# CRITICAL CHECK: If RAG=0 AND KG=0, check if query is general knowledge
rag_count = len(state.get("rag_results", []))
kg_count = len(kg_results)

if rag_count == 0 and kg_count == 0:
    # Check if this is a general knowledge question
    is_general_knowledge = check_patterns(query)
    has_podcast_reference = check_podcast_keywords(query)
    
    if is_general_knowledge and not has_podcast_reference:
        # Block synthesis
        state["should_continue"] = False
        state["answer"] = "I couldn't find information..."
        return state
```

**Patterns Checked**:
- `"what are (the|some|main|key).*issues.*(of|in).*society"`
- `"what are (the|some|main|key).*problems.*(of|in).*society"`
- `"what is (the|a).*solution.*(to|for).*"`
- `"explain.*(society|history|science|philosophy|creativity).*"`

**Podcast Keywords**:
- `["podcast", "transcript", "knowledge graph", "speaker", "episode", "said", "mentioned"]`

**Why**: Even if query planner marks as relevant, if retrieval returns 0 results for a general question → Block synthesis.

---

### 3. **Workflow Routing After KG Retrieval** ✅
**File**: `core_engine/reasoning/langgraph_workflow.py` → `create_retrieval_workflow()`

**Change**: Add conditional edge after KG retrieval to check `should_continue`:
```python
# OLD:
workflow.add_edge("retrieve_rag", "retrieve_kg")
workflow.add_edge("retrieve_kg", "rerank")  # ❌ Always continues

# NEW:
workflow.add_edge("retrieve_rag", "retrieve_kg")

def route_after_kg(state: RetrievalState) -> str:
    """Route after KG retrieval - check if synthesis should be blocked."""
    if not state.get("should_continue", True):
        return END  # ✅ Block synthesis
    return "rerank"

workflow.add_conditional_edges(
    "retrieve_kg",
    route_after_kg,
    {
        END: END,
        "rerank": "rerank",
    }
)
```

**Why**: Allows `retrieve_kg_node()` to set `should_continue=False` and block synthesis.

---

## Flow Diagram

### Before Fix:
```
Query → Planner (marks as relevant) → RAG (0 results) → KG (0 results) → Rerank → Synthesize ❌
                                                                                        ↑
                                                                              Still generates answer!
```

### After Fix:
```
Query → Planner (marks as relevant) → RAG (0 results) → KG (0 results) → Check: General Knowledge? → YES → Block Synthesis ✅
                                                                                                    ↓
                                                                                              Return "couldn't find"
```

---

## Expected Behavior

### Query: "What are issues of society?" (RAG=0, KG=0)

**Flow**:
1. Query Planner: Marks as relevant (LLM is non-deterministic) ✅
2. RAG Retrieval: Returns 0 results ✅
3. KG Retrieval: Returns 0 results ✅
4. **Post-Retrieval Check**: Detects `rag_count=0`, `kg_count=0` ✅
5. **Pattern Check**: Matches `"what are.*issues.*society"` ✅
6. **Podcast Reference Check**: No podcast keywords found ✅
7. **Decision**: `is_general_knowledge=True`, `has_podcast_reference=False` → Block synthesis ✅
8. **Result**: `should_continue=False`, return "I couldn't find information..." ✅

**NO SYNTHESIS HAPPENS** ✅

---

## Files Modified

1. **`core_engine/reasoning/intelligent_query_planner.py`**
   - `_check_domain_relevance()`: Default to `is_relevant=False` on failure

2. **`core_engine/reasoning/langgraph_nodes.py`**
   - `retrieve_kg_node()`: Post-retrieval check for general knowledge questions

3. **`core_engine/reasoning/langgraph_workflow.py`**
   - `create_retrieval_workflow()`: Conditional routing after KG retrieval

---

## Status

✅ **Complete**: Multi-layer protection prevents general knowledge answers when RAG=0, KG=0

**Result**: System will now:
1. **Query Planner**: Default to NOT RELEVANT if check fails (safer)
2. **Post-Retrieval Check**: Block synthesis if RAG=0, KG=0 AND query is general knowledge
3. **Workflow Routing**: Respect `should_continue=False` to block synthesis

---

## Testing

Test with queries that return 0 results:
- "What are issues of society?" → Should return "couldn't find" (NO synthesis)
- "What are problems in society?" → Should return "couldn't find" (NO synthesis)
- "What is the solution to X?" → Should return "couldn't find" if RAG=0, KG=0 (NO synthesis)

**But**:
- "What did Phil Jackson say about society?" → Should proceed (has podcast reference)
- "What are issues of society in the podcasts?" → Should proceed (has podcast reference)

If synthesis still happens, logs will show which check failed.
