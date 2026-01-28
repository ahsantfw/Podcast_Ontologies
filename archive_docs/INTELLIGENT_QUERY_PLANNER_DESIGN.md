# Intelligent Query Planner - Design & Implementation Plan

## Core Requirements

### 1. Context Awareness
- ✅ Understand session context (previous Q&A)
- ✅ Detect follow-up questions vs new questions
- ✅ Use conversation history intelligently

### 2. Domain Awareness
- ✅ Reject irrelevant questions (math, coding, general knowledge)
- ✅ Understand relevance (seems irrelevant but actually relevant)
- ✅ Stay focused on podcast domain

### 3. Intelligence
- ✅ Know when to decompose vs simple answer
- ✅ Understand query complexity
- ✅ Make smart decisions about retrieval strategy

### 4. Performance
- ✅ Don't degrade current speed/accuracy
- ✅ Fast path for simple queries
- ✅ Only use complex planning when needed

---

## Query Planner Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENT QUERY PLANNER                             │
└─────────────────────────────────────────────────────────────────────────┘

USER QUERY + SESSION CONTEXT
        ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: CONTEXT ANALYSIS                                               │
│  • Is this a follow-up?                                                 │
│  • Is this a new question?                                               │
│  • What's the conversation context?                                     │
│  • Extract referenced entities from previous messages                    │
└─────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: DOMAIN RELEVANCE CHECK                                          │
│  • Is this question relevant to podcast domain?                         │
│  • Is this math/coding/general knowledge?                                │
│  • Does it seem irrelevant but might be relevant?                        │
│  • Decision: REJECT or CONTINUE                                         │
└─────────────────────────────────────────────────────────────────────────┘
        ↓ (if CONTINUE)
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: COMPLEXITY ASSESSMENT                                          │
│  • Simple query? (greeting, single entity, definition)                   │
│  • Moderate query? (comparison, multi-entity)                           │
│  • Complex query? (multi-part, causal, cross-episode)                   │
│  • Decision: SIMPLE_PATH or PLANNING_PATH                               │
└─────────────────────────────────────────────────────────────────────────┘
        ↓
    ┌───┴───┐
    │       │
SIMPLE    PLANNING
PATH      PATH
    │       │
    ↓       ↓
┌─────────┐ ┌──────────────────────────────────────────────┐
│ Direct  │ │ Query Decomposition                         │
│ Answer  │ │ • Extract entities                          │
│ (No     │ │ • Identify relationships                     │
│ Retrieval│ │ • Create sub-queries                       │
│ Needed) │ │ • Plan retrieval strategy                  │
└─────────┘ └──────────────────────────────────────────────┘
```

---

## Implementation Design

### Module: `core_engine/reasoning/intelligent_query_planner.py`

```python
"""
Intelligent Query Planner - Context-aware, domain-aware query analysis.
"""
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass
from openai import OpenAI
from core_engine.logging import get_logger

@dataclass
class QueryPlan:
    """Structured query plan."""
    # Context
    is_follow_up: bool
    referenced_entities: List[str]
    conversation_context: str
    
    # Domain
    is_relevant: bool
    rejection_reason: Optional[str] = None
    
    # Complexity
    complexity: Literal["simple", "moderate", "complex"]
    intent: str  # "greeting", "definition", "comparison", "causal", "multi_entity", etc.
    
    # Planning
    needs_decomposition: bool
    sub_queries: List[str]
    entities: List[str]
    relationships_needed: List[str]
    
    # Retrieval Strategy
    retrieval_strategy: Dict[str, Any]
    # {
    #   "use_rag": bool,
    #   "use_kg": bool,
    #   "kg_query_type": "entity_centric" | "multi_hop" | "cross_episode",
    #   "rag_expansion": bool,
    #   "iterative": bool
    # }


class IntelligentQueryPlanner:
    """
    Intelligent query planner that:
    - Understands context (session, conversation)
    - Checks domain relevance
    - Assesses complexity
    - Plans retrieval strategy
    """
    
    def __init__(self, openai_client: OpenAI):
        self.llm = openai_client
        self.logger = get_logger(__name__)
    
    def plan(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """
        Create intelligent query plan.
        
        Args:
            query: User query
            conversation_history: Previous messages
            session_metadata: Session context (entities, user info)
        
        Returns:
            QueryPlan with all analysis
        """
        # Step 1: Context Analysis
        context_analysis = self._analyze_context(query, conversation_history, session_metadata)
        
        # Step 2: Domain Relevance Check
        relevance_check = self._check_domain_relevance(query, context_analysis)
        
        if not relevance_check["is_relevant"]:
            return QueryPlan(
                is_follow_up=context_analysis["is_follow_up"],
                referenced_entities=context_analysis["referenced_entities"],
                conversation_context=context_analysis["context_summary"],
                is_relevant=False,
                rejection_reason=relevance_check["reason"],
                complexity="simple",
                intent="out_of_scope",
                needs_decomposition=False,
                sub_queries=[],
                entities=[],
                relationships_needed=[],
                retrieval_strategy={}
            )
        
        # Step 3: Complexity Assessment
        complexity_analysis = self._assess_complexity(query, context_analysis)
        
        # Step 4: Create Plan
        if complexity_analysis["complexity"] == "simple":
            return self._create_simple_plan(query, context_analysis, complexity_analysis)
        else:
            return self._create_complex_plan(query, context_analysis, complexity_analysis)
    
    def _analyze_context(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]],
        session_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze conversation context."""
        if not conversation_history or len(conversation_history) == 0:
            return {
                "is_follow_up": False,
                "referenced_entities": [],
                "context_summary": "",
                "previous_topics": []
            }
        
        # Analyze last few messages
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        
        # Check if query references previous conversation
        context_prompt = f"""
        Analyze if this query is a follow-up to previous conversation.
        
        Previous messages:
        {self._format_messages(recent_messages)}
        
        Current query: {query}
        
        Determine:
        1. Is this a follow-up question? (references previous answer)
        2. What entities/concepts from previous messages are referenced?
        3. What's the conversation context?
        
        Return JSON:
        {{
            "is_follow_up": bool,
            "referenced_entities": [...],
            "context_summary": "...",
            "previous_topics": [...]
        }}
        """
        
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": context_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Add session metadata entities
        if session_metadata:
            active_entity = session_metadata.get("active_entity")
            if active_entity:
                analysis["referenced_entities"].append(active_entity)
        
        return analysis
    
    def _check_domain_relevance(
        self,
        query: str,
        context_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if query is relevant to podcast domain."""
        
        # Fast path: Check for obvious out-of-scope patterns
        out_of_scope_patterns = [
            r"\b(calculate|math|equation|solve|algebra|geometry|trigonometry|calculus)\b",
            r"(\d+\s*[+\-*/]\s*\d+|x\s*[=+\-*/]|solve for x|what is x)",
            r"\b(code|programming|function|variable|class|import|def |print\(|if __name__)\b",
            r"\b(weather|temperature|forecast|rain|snow)\b",
            r"\b(stock|price|market|trading|bitcoin|crypto)\b",
            r"\b(current events|news|today|yesterday|recent)\b",
        ]
        
        import re
        query_lower = query.lower()
        for pattern in out_of_scope_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return {
                    "is_relevant": False,
                    "reason": "This question is outside the podcast domain (math/coding/general knowledge)."
                }
        
        # LLM-based relevance check (for nuanced cases)
        relevance_prompt = f"""
        You are a Podcast Intelligence Assistant. You ONLY answer questions about:
        - Podcast transcripts and content
        - Concepts, people, and ideas from podcasts
        - Philosophy, creativity, coaching, personal development topics
        
        You CANNOT answer:
        - Math problems
        - Coding questions
        - Current events/news
        - General knowledge questions
        - Weather, sports, etc.
        
        However, if a question SEEMS irrelevant but is actually asking about podcast content, it IS relevant.
        Example: "What did Phil Jackson say about meditation?" - RELEVANT (even if seems like general question)
        Example: "What is 2+2?" - NOT RELEVANT
        
        Query: {query}
        
        Previous context: {context_analysis.get('context_summary', 'None')}
        
        Determine if this query is relevant to podcast domain.
        Consider: Does this question relate to podcast content, even indirectly?
        
        Return JSON:
        {{
            "is_relevant": bool,
            "reason": "explanation",
            "confidence": 0.0-1.0
        }}
        """
        
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": relevance_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    def _assess_complexity(
        self,
        query: str,
        context_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess query complexity."""
        
        # Fast path: Simple queries
        simple_patterns = [
            r"^(hi|hello|hey|thanks|thank you|bye|goodbye)",
            r"^(what is|who is|define)\s+\w+$",  # Simple definition
            r"^\w+\?$",  # Single word question
        ]
        
        import re
        if any(re.match(pattern, query.lower().strip()) for pattern in simple_patterns):
            return {
                "complexity": "simple",
                "intent": "greeting" if re.match(r"^(hi|hello|hey)", query.lower()) else "definition",
                "needs_decomposition": False
            }
        
        # LLM-based complexity assessment
        complexity_prompt = f"""
        Analyze query complexity and intent.
        
        Query: {query}
        Context: {context_analysis.get('context_summary', 'None')}
        
        Complexity levels:
        - SIMPLE: Greeting, single entity definition, yes/no
        - MODERATE: Comparison, multi-entity, causal (single hop)
        - COMPLEX: Multi-part, multi-hop causal, cross-episode analysis
        
        Intent types:
        - greeting
        - definition
        - comparison
        - causal
        - multi_entity
        - cross_episode
        - follow_up
        
        Return JSON:
        {{
            "complexity": "simple" | "moderate" | "complex",
            "intent": "...",
            "needs_decomposition": bool,
            "entities": [...],
            "relationships": [...]
        }}
        """
        
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": complexity_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _create_simple_plan(
        self,
        query: str,
        context_analysis: Dict[str, Any],
        complexity_analysis: Dict[str, Any]
    ) -> QueryPlan:
        """Create plan for simple queries (fast path)."""
        
        # For greetings, no retrieval needed
        if complexity_analysis["intent"] == "greeting":
            return QueryPlan(
                is_follow_up=context_analysis["is_follow_up"],
                referenced_entities=context_analysis["referenced_entities"],
                conversation_context=context_analysis["context_summary"],
                is_relevant=True,
                complexity="simple",
                intent="greeting",
                needs_decomposition=False,
                sub_queries=[query],
                entities=complexity_analysis.get("entities", []),
                relationships_needed=[],
                retrieval_strategy={
                    "use_rag": False,
                    "use_kg": False,
                    "direct_answer": True
                }
            )
        
        # For simple definitions, basic retrieval
        return QueryPlan(
            is_follow_up=context_analysis["is_follow_up"],
            referenced_entities=context_analysis["referenced_entities"],
            conversation_context=context_analysis["context_summary"],
            is_relevant=True,
            complexity="simple",
            intent=complexity_analysis["intent"],
            needs_decomposition=False,
            sub_queries=[query],
            entities=complexity_analysis.get("entities", []),
            relationships_needed=complexity_analysis.get("relationships", []),
            retrieval_strategy={
                "use_rag": True,
                "use_kg": True,
                "kg_query_type": "entity_centric",
                "rag_expansion": False,
                "iterative": False
            }
        )
    
    def _create_complex_plan(
        self,
        query: str,
        context_analysis: Dict[str, Any],
        complexity_analysis: Dict[str, Any]
    ) -> QueryPlan:
        """Create plan for complex queries."""
        
        # Decompose query
        decomposition = self._decompose_query(query, complexity_analysis)
        
        # Determine retrieval strategy
        strategy = self._determine_retrieval_strategy(complexity_analysis, decomposition)
        
        return QueryPlan(
            is_follow_up=context_analysis["is_follow_up"],
            referenced_entities=context_analysis["referenced_entities"],
            conversation_context=context_analysis["context_summary"],
            is_relevant=True,
            complexity=complexity_analysis["complexity"],
            intent=complexity_analysis["intent"],
            needs_decomposition=True,
            sub_queries=decomposition["sub_queries"],
            entities=decomposition["entities"],
            relationships_needed=decomposition["relationships"],
            retrieval_strategy=strategy
        )
    
    def _decompose_query(
        self,
        query: str,
        complexity_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decompose complex query into sub-queries."""
        
        if complexity_analysis["intent"] == "comparison":
            # "How do X and Y differ?" → ["What is X?", "What is Y?"]
            entities = complexity_analysis.get("entities", [])
            sub_queries = [f"What is {entity}?" for entity in entities]
            sub_queries.append(query)  # Also keep original for comparison
        elif complexity_analysis["intent"] == "multi_entity":
            # "What do X, Y, Z have in common?" → separate queries for each
            entities = complexity_analysis.get("entities", [])
            sub_queries = [f"Tell me about {entity}" for entity in entities]
            sub_queries.append(query)  # Also keep original
        elif complexity_analysis["intent"] == "causal":
            # "What leads to X?" → ["What is X?", "What causes X?"]
            sub_queries = [query, f"What causes {query}?"]
        else:
            # Use LLM for decomposition
            decomposition_prompt = f"""
            Decompose this complex query into sub-queries.
            
            Query: {query}
            Intent: {complexity_analysis["intent"]}
            Entities: {complexity_analysis.get("entities", [])}
            
            Create 2-4 sub-queries that together answer the original query.
            
            Return JSON:
            {{
                "sub_queries": [...],
                "entities": [...],
                "relationships": [...]
            }}
            """
            
            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": decomposition_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
        
        return {
            "sub_queries": sub_queries,
            "entities": complexity_analysis.get("entities", []),
            "relationships": complexity_analysis.get("relationships", [])
        }
    
    def _determine_retrieval_strategy(
        self,
        complexity_analysis: Dict[str, Any],
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine optimal retrieval strategy."""
        
        intent = complexity_analysis["intent"]
        entities = decomposition.get("entities", [])
        
        strategy = {
            "use_rag": True,
            "use_kg": True,
            "rag_expansion": len(entities) > 1,  # Expand for multi-entity
            "iterative": complexity_analysis["complexity"] == "complex"
        }
        
        # KG query type based on intent
        if intent == "multi_entity" or len(entities) > 1:
            strategy["kg_query_type"] = "multi_hop"
        elif intent == "causal":
            strategy["kg_query_type"] = "multi_hop"  # Need to traverse relationships
        elif intent == "cross_episode":
            strategy["kg_query_type"] = "cross_episode"
        else:
            strategy["kg_query_type"] = "entity_centric"
        
        return strategy
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for context."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]  # Truncate
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
```

---

## Integration with Current System

### Updated Agent Flow

```python
# In agent.py _handle_knowledge_query method

def _handle_knowledge_query(self, query: str, ...):
    # Step 1: Intelligent Query Planning
    plan = self.query_planner.plan(
        query=query,
        conversation_history=conversation_history,
        session_metadata=session_metadata
    )
    
    # Step 2: Check if out of scope
    if not plan.is_relevant:
        return self._handle_out_of_scope(query, plan.rejection_reason)
    
    # Step 3: Fast path for simple queries
    if plan.complexity == "simple" and plan.retrieval_strategy.get("direct_answer"):
        # Direct answer, no retrieval
        return self._handle_simple_query(query, plan, conversation_history)
    
    # Step 4: Enhanced retrieval based on plan
    rag_results = []
    kg_results = []
    
    if plan.retrieval_strategy["use_rag"]:
        # Use sub-queries if decomposed
        queries_to_retrieve = plan.sub_queries if plan.needs_decomposition else [query]
        
        for q in queries_to_retrieve:
            results = self.hybrid_retriever.retrieve(q, use_vector=True, use_graph=False)
            rag_results.extend(results)
        
        # Query expansion if needed
        if plan.retrieval_strategy.get("rag_expansion"):
            expanded_queries = self._expand_query(query)
            for eq in expanded_queries:
                results = self.hybrid_retriever.retrieve(eq, use_vector=True, use_graph=False)
                rag_results.extend(results)
    
    if plan.retrieval_strategy["use_kg"]:
        # Use KG optimizer based on plan
        kg_query_type = plan.retrieval_strategy["kg_query_type"]
        
        if kg_query_type == "entity_centric":
            for entity in plan.entities:
                results = self.kg_optimizer.entity_centric_query(entity)
                kg_results.extend(results)
        elif kg_query_type == "multi_hop":
            results = self.kg_optimizer.multi_hop_query(query, plan.entities)
            kg_results.extend(results)
        elif kg_query_type == "cross_episode":
            # Cross-episode query
            pass
    
    # Continue with reranking, synthesis...
```

---

## LangGraph Integration (Future Architecture)

### LangGraph State

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class QueryState(TypedDict):
    query: str
    conversation_history: List[Dict]
    session_metadata: Dict
    query_plan: QueryPlan
    rag_results: List[Dict]
    kg_results: List[Dict]
    final_answer: str
```

### LangGraph Flow

```python
def create_retrieval_graph():
    workflow = StateGraph(QueryState)
    
    # Node 1: Query Planning
    workflow.add_node("plan_query", plan_query_node)
    
    # Node 2: Domain Check
    workflow.add_node("check_domain", check_domain_node)
    
    # Node 3: Route based on complexity
    workflow.add_conditional_edges(
        "check_domain",
        route_by_complexity,
        {
            "simple": "simple_retrieval",
            "complex": "complex_retrieval",
            "out_of_scope": "reject_query"
        }
    )
    
    # Node 4: Retrieval (parallel)
    workflow.add_node("simple_retrieval", simple_retrieval_node)
    workflow.add_node("complex_retrieval", complex_retrieval_node)
    
    # Node 5: Reranking
    workflow.add_node("rerank", rerank_node)
    
    # Node 6: Synthesis
    workflow.add_node("synthesize", synthesize_node)
    
    # Edges
    workflow.set_entry_point("plan_query")
    workflow.add_edge("plan_query", "check_domain")
    workflow.add_edge("simple_retrieval", "rerank")
    workflow.add_edge("complex_retrieval", "rerank")
    workflow.add_edge("rerank", "synthesize")
    workflow.add_edge("synthesize", END)
    workflow.add_edge("reject_query", END)
    
    return workflow.compile()
```

**Note**: LangGraph integration can be Phase 2. Start with current architecture, then migrate.

---

## Implementation Plan

### Phase 1: Intelligent Query Planner (Week 1)

**Day 1-2: Core Planner**
- [ ] Create `intelligent_query_planner.py`
- [ ] Implement context analysis
- [ ] Implement domain relevance check
- [ ] Implement complexity assessment
- [ ] Unit tests

**Day 3: Integration**
- [ ] Integrate into `agent.py`
- [ ] Update `_handle_knowledge_query`
- [ ] Add fast path for simple queries
- [ ] Integration tests

**Day 4-5: Refinement**
- [ ] Tune prompts
- [ ] Optimize performance (caching, fast paths)
- [ ] Test with real queries
- [ ] Measure accuracy/speed impact

---

### Phase 2: Enhanced Retrieval (Week 2)

**Day 1-2: KG Query Optimizer**
- [ ] Create `kg_query_optimizer.py`
- [ ] Implement entity linking
- [ ] Implement multi-hop queries
- [ ] Implement cross-episode queries

**Day 3: Query Expansion**
- [ ] Create `query_expander.py`
- [ ] Implement query variation generation
- [ ] Integrate multi-query retrieval

**Day 4-5: Reranking**
- [ ] Create `reranker.py`
- [ ] Implement RRF
- [ ] Integrate into pipeline

---

### Phase 3: Testing & Optimization (Week 3)

**Day 1-2: Testing**
- [ ] Test simple queries (should be fast)
- [ ] Test complex queries (should work)
- [ ] Test follow-up questions
- [ ] Test out-of-scope rejection

**Day 3-4: Performance**
- [ ] Measure latency impact
- [ ] Optimize LLM calls (batch, cache)
- [ ] Ensure no degradation

**Day 5: Documentation**
- [ ] Document query planner
- [ ] Create usage examples
- [ ] Update architecture docs

---

## Performance Considerations

### Fast Paths (No LLM Calls)

1. **Greetings**: Pattern match → direct answer
2. **Out-of-scope patterns**: Regex check → reject
3. **Simple definitions**: Pattern match → basic retrieval

### Caching Strategy

```python
# Cache query plans for similar queries
from functools import lru_cache

@lru_cache(maxsize=100)
def _cached_plan(self, query_hash: str, context_hash: str):
    # Cache plans for similar queries
    pass
```

### LLM Call Optimization

- Use `gpt-4o-mini` for planning (faster, cheaper)
- Batch similar operations
- Cache common patterns

---

## Success Criteria

### Accuracy
- ✅ Simple queries: Same or better accuracy
- ✅ Complex queries: 60% → 85%+ success rate
- ✅ Follow-up questions: Properly handled
- ✅ Out-of-scope: Correctly rejected

### Performance
- ✅ Simple queries: < 100ms overhead
- ✅ Complex queries: < 500ms overhead
- ✅ No degradation in current speed

### Quality
- ✅ Context awareness: Follow-ups work
- ✅ Domain awareness: Irrelevant questions rejected
- ✅ Intelligence: Right strategy for each query

---

## Migration Strategy

### Step 1: Add Query Planner (Non-Breaking)
- Add planner as optional component
- Current flow still works
- New flow uses planner when available

### Step 2: Gradual Migration
- Test with subset of queries
- Compare accuracy/speed
- Gradually enable for all queries

### Step 3: LangGraph (Future)
- Once planner is stable
- Migrate to LangGraph architecture
- Better orchestration and debugging

---

## Risk Mitigation

### Risk: Performance Degradation
**Mitigation**: 
- Fast paths for simple queries
- Caching
- Use faster LLM model
- Measure before/after

### Risk: Over-Engineering
**Mitigation**:
- Start simple
- Add complexity only if needed
- Fast paths avoid unnecessary processing

### Risk: Breaking Current System
**Mitigation**:
- Non-breaking integration
- Feature flag to enable/disable
- Gradual rollout
