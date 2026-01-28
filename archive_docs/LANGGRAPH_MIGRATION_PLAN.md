# LangGraph Migration Plan: Evolve, Don't Rebuild

## 🎯 Recommendation: **IMPROVE/EVOLVE Current System**

### Why NOT Rebuild from Scratch?

✅ **Current System Works Well**:
- `HybridRetriever` - Solid RAG + KG retrieval
- `PodcastAgent` - LLM brain working
- Parallel RAG + KG searches already implemented
- Streaming responses working
- Session management functional

✅ **Risk of Rebuilding**:
- Lose working code
- Risk breaking existing functionality
- Waste time rebuilding what works
- Potential accuracy degradation

✅ **Better Approach**:
- **Wrap** existing components in LangGraph nodes
- **Add** new components (Query Planner, Reranker)
- **Enhance** current components incrementally
- **Preserve** all existing functionality

---

## Architecture: LangGraph Wrapper

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH ORCHESTRATION                           │
│                    (New Layer - Orchestrates Everything)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ Query Planner │          │   Retrieval   │          │   Synthesis   │
│    (NEW)      │          │   (EXISTING)  │          │   (EXISTING)  │
│               │          │               │          │               │
│ • Context     │          │ • HybridRetr. │          │ • PodcastAgent│
│ • Domain      │          │ • RAG (Qdrant)│          │ • LLM         │
│ • Complexity  │          │ • KG (Neo4j)  │          │ • Sources     │
└───────────────┘          └───────────────┘          └───────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                            ┌───────┴───────┐
                            ▼               ▼
                    ┌───────────────┐ ┌───────────────┐
                    │   Reranker    │ │ KG Optimizer  │
                    │    (NEW)      │ │   (ENHANCED)  │
                    │               │ │               │
                    │ • RRF         │ │ • Multi-hop   │
                    │ • Combine     │ │ • Cross-ep    │
                    └───────────────┘ └───────────────┘
```

---

## Implementation Strategy

### Phase 1: Wrap Existing Components (Week 1)

**Goal**: Create LangGraph nodes that use existing components

#### 1.1 Create LangGraph State

```python
# core_engine/reasoning/langgraph_state.py
from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class QueryPlan:
    """Query plan from intelligent planner."""
    is_follow_up: bool
    is_relevant: bool
    complexity: str  # "simple", "moderate", "complex"
    intent: str
    needs_decomposition: bool
    sub_queries: List[str]
    entities: List[str]
    retrieval_strategy: Dict[str, Any]

class RetrievalState(TypedDict):
    """State passed through LangGraph."""
    # Input
    query: str
    conversation_history: List[Dict[str, Any]]
    session_metadata: Dict[str, Any]
    
    # Planning
    query_plan: Optional[QueryPlan]
    
    # Retrieval
    rag_results: List[Dict[str, Any]]
    kg_results: List[Dict[str, Any]]
    
    # Processing
    reranked_results: List[Dict[str, Any]]
    
    # Output
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    # Control flow
    should_continue: bool
    error: Optional[str]
```

#### 1.2 Create LangGraph Nodes (Wrapping Existing)

```python
# core_engine/reasoning/langgraph_nodes.py
from langgraph.graph import StateGraph, END
from core_engine.reasoning.intelligent_query_planner import IntelligentQueryPlanner
from core_engine.reasoning.hybrid_retriever import HybridRetriever
from core_engine.reasoning.agent import PodcastAgent
from core_engine.reasoning.langgraph_state import RetrievalState, QueryPlan

def plan_query_node(state: RetrievalState) -> RetrievalState:
    """Node 1: Intelligent Query Planning."""
    planner = IntelligentQueryPlanner(openai_client=state["openai_client"])
    
    plan = planner.plan(
        query=state["query"],
        conversation_history=state["conversation_history"],
        session_metadata=state["session_metadata"]
    )
    
    state["query_plan"] = plan
    
    # Fast path: Out of scope
    if not plan.is_relevant:
        state["should_continue"] = False
        state["answer"] = f"I can only answer questions about podcast content. {plan.rejection_reason}"
        return state
    
    return state

def retrieve_rag_node(state: RetrievalState) -> RetrievalState:
    """Node 2: RAG Retrieval (using existing HybridRetriever)."""
    retriever: HybridRetriever = state["hybrid_retriever"]
    plan: QueryPlan = state["query_plan"]
    
    # Use existing retrieve method
    if plan.retrieval_strategy.get("use_rag"):
        queries = plan.sub_queries if plan.needs_decomposition else [state["query"]]
        
        rag_results = []
        for q in queries:
            results = retriever.retrieve(q, use_vector=True, use_graph=False)
            rag_results.extend(results)
        
        state["rag_results"] = rag_results
    
    return state

def retrieve_kg_node(state: RetrievalState) -> RetrievalState:
    """Node 3: KG Retrieval (using existing Neo4jClient)."""
    neo4j_client = state["neo4j_client"]
    plan: QueryPlan = state["query_plan"]
    
    # Use existing KG search logic (from agent.py)
    if plan.retrieval_strategy.get("use_kg"):
        kg_results = []
        
        # Enhanced KG queries based on plan
        if plan.retrieval_strategy["kg_query_type"] == "entity_centric":
            # Use existing _search_knowledge_graph logic
            for entity in plan.entities:
                results = _search_knowledge_graph_enhanced(neo4j_client, entity)
                kg_results.extend(results)
        elif plan.retrieval_strategy["kg_query_type"] == "multi_hop":
            # New multi-hop logic
            results = _multi_hop_query(neo4j_client, plan.entities)
            kg_results.extend(results)
        
        state["kg_results"] = kg_results
    
    return state

def rerank_node(state: RetrievalState) -> RetrievalState:
    """Node 4: Reranking (NEW component)."""
    from core_engine.reasoning.reranker import Reranker
    
    reranker = Reranker()
    reranked = reranker.rerank(
        rag_results=state["rag_results"],
        kg_results=state["kg_results"]
    )
    
    state["reranked_results"] = reranked
    return state

def synthesize_node(state: RetrievalState) -> RetrievalState:
    """Node 5: Synthesis (using existing PodcastAgent)."""
    agent: PodcastAgent = state["podcast_agent"]
    
    # Use existing synthesis logic
    response = agent._synthesize_answer(
        query=state["query"],
        rag_results=state["reranked_results"],
        kg_results=state["kg_results"],
        conversation_history=state["conversation_history"]
    )
    
    state["answer"] = response.answer
    state["sources"] = response.sources
    state["metadata"] = response.metadata
    
    return state
```

#### 1.3 Create LangGraph Workflow

```python
# core_engine/reasoning/langgraph_workflow.py
from langgraph.graph import StateGraph, END
from core_engine.reasoning.langgraph_nodes import (
    plan_query_node,
    retrieve_rag_node,
    retrieve_kg_node,
    rerank_node,
    synthesize_node
)
from core_engine.reasoning.langgraph_state import RetrievalState

def create_retrieval_workflow():
    """Create LangGraph workflow for retrieval."""
    workflow = StateGraph(RetrievalState)
    
    # Add nodes
    workflow.add_node("plan_query", plan_query_node)
    workflow.add_node("retrieve_rag", retrieve_rag_node)
    workflow.add_node("retrieve_kg", retrieve_kg_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("synthesize", synthesize_node)
    
    # Define edges
    workflow.set_entry_point("plan_query")
    
    # Route after planning
    def route_after_planning(state: RetrievalState):
        if not state.get("should_continue", True):
            return END
        return "retrieve_rag"
    
    workflow.add_conditional_edges(
        "plan_query",
        route_after_planning
    )
    
    # Parallel retrieval
    workflow.add_edge("retrieve_rag", "retrieve_kg")
    workflow.add_edge("retrieve_kg", "rerank")
    workflow.add_edge("rerank", "synthesize")
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()
```

#### 1.4 Integrate into Existing System

```python
# core_engine/reasoning/reasoning.py (MODIFY)
class KGReasoner:
    def __init__(self, ...):
        # ... existing init ...
        
        # NEW: LangGraph workflow (optional)
        self.use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
        if self.use_langgraph:
            from core_engine.reasoning.langgraph_workflow import create_retrieval_workflow
            self.langgraph_workflow = create_retrieval_workflow()
    
    def query_streaming(self, query: str, ...):
        """Query with streaming (enhanced with LangGraph)."""
        
        if self.use_langgraph:
            # Use LangGraph workflow
            return self._query_with_langgraph_streaming(query, ...)
        else:
            # Use existing flow (backward compatible)
            return self._query_existing_streaming(query, ...)
    
    def _query_with_langgraph_streaming(self, query: str, ...):
        """Query using LangGraph workflow."""
        # Prepare state
        state = {
            "query": query,
            "conversation_history": conversation_history,
            "session_metadata": session_metadata,
            "hybrid_retriever": self.hybrid_retriever,
            "neo4j_client": self.neo4j_client,
            "podcast_agent": self.agent,
            "openai_client": self.agent.openai_client,
            "rag_results": [],
            "kg_results": [],
            "should_continue": True,
        }
        
        # Run workflow
        final_state = self.langgraph_workflow.invoke(state)
        
        # Stream response
        yield from self._stream_response(final_state)
```

---

### Phase 2: Add New Components (Week 2)

#### 2.1 Intelligent Query Planner
**File**: `core_engine/reasoning/intelligent_query_planner.py` (NEW)

- Context analysis
- Domain relevance check
- Complexity assessment
- Query decomposition

#### 2.2 Reranker
**File**: `core_engine/reasoning/reranker.py` (NEW)

- RRF algorithm
- Combine RAG + KG results
- Reorder by relevance

#### 2.3 KG Query Optimizer
**File**: `core_engine/reasoning/kg_query_optimizer.py` (NEW)

- Multi-hop queries
- Cross-episode queries
- Entity linking

---

### Phase 3: Enhance Existing Components (Week 3)

#### 3.1 Enhance HybridRetriever
**File**: `core_engine/reasoning/hybrid_retriever.py` (MODIFY)

**Add**:
- Query expansion support
- Multi-query retrieval
- Better diversity

**Keep**:
- All existing functionality
- Same interface
- Backward compatible

#### 3.2 Enhance PodcastAgent
**File**: `core_engine/reasoning/agent.py` (MODIFY)

**Add**:
- Better source extraction
- Enhanced synthesis prompts
- Quality checks

**Keep**:
- All existing functionality
- Same interface
- Backward compatible

---

## Migration Path

### Step 1: Add LangGraph (Non-Breaking)
- ✅ Create LangGraph nodes wrapping existing components
- ✅ Feature flag: `USE_LANGGRAPH=false` (default)
- ✅ Current system continues to work
- ✅ Test LangGraph in parallel

### Step 2: Add New Components
- ✅ Query Planner
- ✅ Reranker
- ✅ KG Optimizer
- ✅ Integrate into LangGraph nodes

### Step 3: Enable LangGraph (Gradual)
- ✅ Enable for subset of queries
- ✅ Compare accuracy/speed
- ✅ Fix issues
- ✅ Gradually expand

### Step 4: Full Migration
- ✅ Enable LangGraph for all queries
- ✅ Monitor performance
- ✅ Optimize as needed

---

## Code Structure

```
core_engine/reasoning/
├── langgraph_state.py          # NEW - State definition
├── langgraph_nodes.py           # NEW - LangGraph nodes
├── langgraph_workflow.py        # NEW - Workflow definition
├── intelligent_query_planner.py # NEW - Query planning
├── reranker.py                  # NEW - Reranking
├── kg_query_optimizer.py        # NEW - Enhanced KG queries
├── hybrid_retriever.py          # MODIFY - Enhance existing
├── agent.py                     # MODIFY - Enhance existing
└── reasoning.py                 # MODIFY - Integrate LangGraph
```

---

## Benefits of This Approach

### ✅ Preserves Existing System
- All current code continues to work
- No breaking changes
- Backward compatible

### ✅ Incremental Enhancement
- Add new components gradually
- Test each component independently
- Roll out incrementally

### ✅ LangGraph Benefits
- Better orchestration
- Easier debugging
- Visual workflow
- State management

### ✅ Performance Maintained
- Fast paths preserved
- No unnecessary overhead
- Can disable LangGraph if issues

---

## Risk Mitigation

### Risk: LangGraph Overhead
**Mitigation**: 
- Feature flag to disable
- Measure performance
- Optimize if needed

### Risk: Breaking Existing System
**Mitigation**:
- Non-breaking integration
- Feature flag
- Gradual rollout
- Extensive testing

### Risk: Complexity
**Mitigation**:
- Clear separation of concerns
- Well-documented
- Incremental migration

---

## Success Criteria

### Week 1
- ✅ LangGraph workflow created
- ✅ Existing components wrapped
- ✅ Feature flag working
- ✅ No performance degradation

### Week 2
- ✅ Query Planner integrated
- ✅ Reranker integrated
- ✅ KG Optimizer integrated
- ✅ Accuracy improved

### Week 3
- ✅ Full LangGraph migration
- ✅ Performance maintained
- ✅ Accuracy improved
- ✅ System stable

---

## Next Steps

1. **Create LangGraph State** (`langgraph_state.py`)
2. **Create LangGraph Nodes** (`langgraph_nodes.py`) - Wrap existing components
3. **Create LangGraph Workflow** (`langgraph_workflow.py`)
4. **Integrate into Reasoning** (`reasoning.py`) - Feature flag
5. **Add Query Planner** (`intelligent_query_planner.py`)
6. **Add Reranker** (`reranker.py`)
7. **Add KG Optimizer** (`kg_query_optimizer.py`)
8. **Test & Refine**

---

## Conclusion

**Strategy**: **Evolve, Don't Rebuild**

- ✅ Wrap existing components in LangGraph
- ✅ Add new components incrementally
- ✅ Enhance existing components
- ✅ Preserve all functionality
- ✅ Maintain performance
- ✅ Gradual migration

This approach gives us:
- LangGraph benefits (orchestration, debugging)
- Preserved existing system (no risk)
- Incremental enhancement (manageable)
- Performance maintained (fast paths)

**Ready to start implementing?**
