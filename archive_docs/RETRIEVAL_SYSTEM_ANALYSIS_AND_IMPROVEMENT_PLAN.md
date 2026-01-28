# Retrieval System Analysis & Comprehensive Improvement Plan

## Executive Summary

**Current State**: Basic hybrid retrieval (RAG + KG) with parallel execution, simple fusion, and basic synthesis.

**Client Feedback**: 
- ✅ Accuracy for quotes/summaries is good
- ❌ Cannot handle overly complicated questions
- ❌ KG not being utilized correctly

**Goal**: Build the **best-in-class retrieval system** with maximum accuracy through advanced RAG techniques, optimized KG querying, intelligent reranking, and superior synthesis.

---

## Part 1: Current System Analysis

### 1.1 Current RAG Implementation

**Location**: `core_engine/reasoning/hybrid_retriever.py`

**What Works**:
- ✅ Vector search using OpenAI embeddings (`text-embedding-3-large`)
- ✅ Qdrant vector database integration
- ✅ Basic workspace filtering
- ✅ Result diversity by episode

**What's Missing**:
- ❌ No query expansion/rewriting
- ❌ No query decomposition for complex questions
- ❌ No iterative retrieval (single-pass only)
- ❌ No self-reflection or self-grading
- ❌ No reranking (uses simple score fusion)
- ❌ No query planning (direct embedding of user query)
- ❌ No corrective RAG (no feedback loop)

**Current Flow**:
```
User Query → Embed → Vector Search → Return Top-K
```

**Problems**:
1. **Simple Query Embedding**: Directly embeds user query without expansion
2. **No Query Understanding**: Doesn't decompose complex questions
3. **Single Retrieval Pass**: No iterative refinement
4. **No Reranking**: Uses raw similarity scores
5. **No Quality Check**: Doesn't verify if retrieved results answer the question

---

### 1.2 Current KG Implementation

**Location**: `core_engine/reasoning/agent.py` (`_search_knowledge_graph`)

**What Works**:
- ✅ Basic keyword matching on concept names/descriptions
- ✅ Relationship traversal (outgoing/incoming)
- ✅ Workspace filtering
- ✅ Single optimized Cypher query

**What's Missing**:
- ❌ **No semantic KG search** (only keyword matching)
- ❌ **No multi-hop reasoning** (limited relationship traversal)
- ❌ **No cross-episode concept queries** (doesn't leverage episode_ids effectively)
- ❌ **No implicit relationship discovery** (only explicit relationships)
- ❌ **No query planning for KG** (doesn't understand what KG query to make)
- ❌ **No entity linking** (doesn't map query entities to KG entities)
- ❌ **No temporal/episode-aware queries** (doesn't use episode context)

**Current Cypher Query**:
```cypher
MATCH (c)
WHERE c.workspace_id = $workspace_id
  AND (ANY(term IN $search_terms WHERE toLower(c.name) CONTAINS term)
       OR ANY(term IN $search_terms WHERE toLower(c.description) CONTAINS term))
OPTIONAL MATCH (c)-[r]->(related)
RETURN c.name, c.description, relationships
LIMIT 10
```

**Problems**:
1. **Keyword-only**: No semantic understanding of query intent
2. **Shallow traversal**: Only 1-hop relationships
3. **No episode context**: Doesn't filter/rank by episode relevance
4. **No entity resolution**: Doesn't map "Phil Jackson" → KG entity
5. **No relationship inference**: Can't find implicit connections

---

### 1.3 Current Fusion & Synthesis

**Location**: `core_engine/reasoning/hybrid_retriever.py` (`_fuse_results`), `agent.py` (`_synthesize_answer`)

**What Works**:
- ✅ Basic score fusion (weighted combination)
- ✅ Diversity by episode
- ✅ LLM-based synthesis with style/tone

**What's Missing**:
- ❌ **No reranking** (RRF, cross-encoder, etc.)
- ❌ **No result quality assessment**
- ❌ **No source verification**
- ❌ **Limited ground truth display** (episode/timestamp extraction exists but not optimized)
- ❌ **No synthesis quality check**

---

## Part 2: Advanced RAG Concepts to Implement

### 2.1 Query Planning & Decomposition

**Purpose**: Break complex questions into sub-queries, understand query intent.

**Implementation Strategy**:

```python
class QueryPlanner:
    """Decompose complex queries into sub-queries."""
    
    def plan_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query and create retrieval plan.
        
        Returns:
            {
                "intent": "comparison" | "causal" | "definition" | "multi_entity",
                "sub_queries": [...],
                "entities": [...],
                "relationships_needed": [...],
                "complexity": "simple" | "moderate" | "complex"
            }
        """
```

**Example**:
- Query: "How do Phil Jackson and Rick Rubin approach creativity differently?"
- Plan:
  - Intent: `multi_entity_comparison`
  - Sub-queries: ["Phil Jackson creativity", "Rick Rubin creativity"]
  - Entities: ["Phil Jackson", "Rick Rubin"]
  - Relationships: ["HAS_PRACTICE", "LEADS_TO"]

---

### 2.2 Query Expansion & Rewriting

**Purpose**: Generate multiple query variations for better retrieval.

**Implementation**:
- Use LLM to generate query variations
- Expand with synonyms, related terms
- Create query-specific embeddings

**Example**:
- Original: "creativity"
- Expanded: ["creative process", "artistic innovation", "creative practices", "innovation methods"]

---

### 2.3 Iterative Retrieval

**Purpose**: Refine retrieval based on initial results.

**Flow**:
```
Query → Initial Retrieval → Analyze Gaps → Refined Query → Re-retrieve → Merge Results
```

**Implementation**:
- First pass: Broad retrieval
- Analyze: What's missing? What entities weren't found?
- Second pass: Targeted retrieval for gaps
- Merge and deduplicate

---

### 2.4 Self-Reflection & Self-Grading

**Purpose**: Assess retrieval quality before synthesis.

**Components**:
1. **Retrieval Quality Check**: Do results answer the question?
2. **Coverage Check**: Are all entities covered?
3. **Relevance Scoring**: Rate each result's relevance
4. **Gap Detection**: Identify missing information

**Implementation**:
```python
class RetrievalGrader:
    """Grade retrieval quality and identify gaps."""
    
    def grade_retrieval(
        self, 
        query: str, 
        results: List[Dict], 
        entities: List[str]
    ) -> Dict[str, Any]:
        """
        Returns:
            {
                "quality_score": 0.0-1.0,
                "coverage": {"entity": bool},
                "relevance_scores": [...],
                "gaps": [...],
                "should_retry": bool
            }
        """
```

---

### 2.5 Corrective RAG

**Purpose**: Fix retrieval errors through feedback loop.

**Flow**:
```
Retrieve → Grade → If Poor → Identify Issues → Correct Query → Re-retrieve
```

**Correction Strategies**:
- Query rewriting if low relevance
- Entity resolution if entities not found
- Relationship expansion if connections missing

---

### 2.6 Reranking

**Purpose**: Improve result ordering using advanced algorithms.

**Methods to Implement**:

1. **RRF (Reciprocal Rank Fusion)**
   ```python
   def reciprocal_rank_fusion(results_list: List[List[Dict]], k: int = 60):
       """Combine multiple ranked lists using RRF."""
   ```

2. **Cross-Encoder Reranking**
   - Use smaller model (e.g., `cross-encoder/ms-marco-MiniLM`)
   - Score each (query, result) pair
   - Reorder by cross-encoder scores

3. **Hybrid Scoring**
   - Combine: Vector similarity + KG relevance + Cross-encoder + Metadata boost

---

## Part 3: KG Query Optimization

### 3.1 Semantic KG Search

**Current**: Keyword matching only
**Needed**: Semantic understanding

**Implementation**:
- Embed query → Find similar concept embeddings in KG
- Use vector similarity for concept matching
- Combine with keyword matching

---

### 3.2 Multi-Hop Reasoning

**Current**: 1-hop relationships only
**Needed**: Multi-hop traversal

**Example Query**: "What practices lead to outcomes that Phil Jackson uses?"
- 1-hop: Phil Jackson → Practices
- 2-hop: Practices → Outcomes
- 3-hop: Outcomes → Related Concepts

**Cypher Pattern**:
```cypher
MATCH path = (start:Concept)-[*1..3]->(end:Concept)
WHERE start.name CONTAINS $entity
  AND end.type = 'Outcome'
RETURN path, length(path) as hops
ORDER BY hops, relevance_score
```

---

### 3.3 Cross-Episode Concept Queries

**Purpose**: Find concepts that appear across multiple episodes.

**Implementation**:
- Query concepts by episode_ids
- Rank by episode frequency
- Show episode diversity

**Cypher**:
```cypher
MATCH (c:Concept)
WHERE c.workspace_id = $workspace_id
  AND size(c.episode_ids) > 1  // Cross-episode
  AND ANY(ep_id IN c.episode_ids WHERE ep_id IN $relevant_episodes)
RETURN c, size(c.episode_ids) as episode_count
ORDER BY episode_count DESC, relevance_score DESC
```

---

### 3.4 Implicit Relationship Discovery

**Current**: Only explicit relationships
**Needed**: Infer implicit connections

**Strategies**:
1. **Co-occurrence**: Concepts mentioned together → implicit relationship
2. **Semantic similarity**: Similar embeddings → implicit similarity
3. **Temporal proximity**: Concepts in same episode/timestamp → implicit connection

---

### 3.5 Entity Linking & Resolution

**Purpose**: Map query entities to KG entities.

**Implementation**:
```python
class EntityLinker:
    """Link query entities to KG entities."""
    
    def link_entities(self, query: str) -> Dict[str, str]:
        """
        Returns:
            {
                "Phil Jackson": "concept_id_123",
                "creativity": "concept_id_456"
            }
        """
```

---

### 3.6 Query-Specific KG Strategies

**Different query types need different KG queries**:

1. **Definition Query**: "What is X?"
   - Find concept node
   - Get description, relationships

2. **Comparison Query**: "How do X and Y differ?"
   - Find both concepts
   - Compare relationships, properties

3. **Causal Query**: "What leads to X?"
   - Traverse relationships backwards
   - Find causes/predecessors

4. **Multi-Entity Query**: "What do X, Y, Z have in common?"
   - Find common relationships
   - Find intersection of properties

---

## Part 4: Synthesis Improvements

### 4.1 Enhanced Ground Truth Display

**Current**: Basic episode/timestamp extraction
**Needed**: Comprehensive source attribution

**Requirements**:
- Episode ID with readable name
- Exact timestamp
- Speaker name
- Quote text with context
- Source confidence score

**Format**:
```
[Source 1] Episode: "Tyler Cowen Part 1" | Timestamp: 00:15:32 | Speaker: Tyler Cowen
"Exact quote text here..."
```

---

### 4.2 Synthesis Quality Checks

**Before Finalizing Answer**:
1. Verify all citations are from provided sources
2. Check entity coverage
3. Validate quote accuracy
4. Ensure no hallucination

---

### 4.3 Multi-Pass Synthesis

**Strategy**:
1. **First Pass**: Draft answer
2. **Verification**: Check against sources
3. **Refinement**: Fix inaccuracies
4. **Final Pass**: Polish with citations

---

## Part 5: Implementation Plan

### Phase 1: Foundation (Week 1-2)

**Priority: HIGH**

1. **Query Planning Module**
   - Create `query_planner.py`
   - Implement query decomposition
   - Intent classification enhancement

2. **Reranking Module**
   - Implement RRF
   - Add cross-encoder reranking option
   - Create `reranker.py`

3. **Entity Linking**
   - Create `entity_linker.py`
   - Map query entities to KG entities
   - Handle aliases and variations

---

### Phase 2: Advanced RAG (Week 3-4)

**Priority: HIGH**

1. **Query Expansion**
   - LLM-based query rewriting
   - Synonym expansion
   - Multi-query retrieval

2. **Iterative Retrieval**
   - Implement retrieval loop
   - Gap detection
   - Refined re-retrieval

3. **Self-Grading**
   - Create `retrieval_grader.py`
   - Quality assessment
   - Coverage checking

---

### Phase 3: KG Optimization (Week 5-6)

**Priority: HIGH**

1. **Semantic KG Search**
   - Add embedding-based concept matching
   - Hybrid keyword + semantic search

2. **Multi-Hop Reasoning**
   - Implement path traversal
   - Variable-depth queries
   - Path relevance scoring

3. **Cross-Episode Queries**
   - Episode-aware ranking
   - Cross-episode concept discovery
   - Episode diversity optimization

4. **Implicit Relationships**
   - Co-occurrence analysis
   - Semantic similarity relationships
   - Temporal proximity relationships

---

### Phase 4: Synthesis & Quality (Week 7-8)

**Priority: MEDIUM**

1. **Enhanced Ground Truth**
   - Improve source extraction
   - Better timestamp handling
   - Speaker resolution

2. **Synthesis Quality Checks**
   - Citation verification
   - Hallucination detection
   - Multi-pass refinement

3. **Corrective RAG**
   - Feedback loop implementation
   - Query correction strategies
   - Re-retrieval triggers

---

### Phase 5: Integration & Testing (Week 9-10)

**Priority: HIGH**

1. **Integration**
   - Wire all components together
   - End-to-end testing
   - Performance optimization

2. **Evaluation**
   - Create test suite
   - Measure accuracy improvements
   - Compare before/after

3. **Documentation**
   - API documentation
   - Usage examples
   - Architecture diagrams

---

## Part 6: Technical Architecture

### 6.1 New Module Structure

```
core_engine/reasoning/
├── query_planner.py          # Query decomposition & planning
├── query_expander.py         # Query rewriting & expansion
├── entity_linker.py         # Entity resolution
├── retrieval_grader.py      # Self-grading & quality checks
├── reranker.py              # RRF, cross-encoder reranking
├── iterative_retriever.py   # Multi-pass retrieval
├── corrective_rag.py        # Feedback loop & correction
├── kg_query_optimizer.py    # Advanced KG querying
└── synthesis_enhancer.py    # Improved synthesis
```

---

### 6.2 Enhanced Retrieval Flow

```
User Query
    ↓
Query Planner (decompose, understand intent)
    ↓
Entity Linker (map to KG entities)
    ↓
Query Expander (generate variations)
    ↓
┌─────────────────────────────────────┐
│   Parallel Retrieval                │
│   - RAG (vector + expanded queries) │
│   - KG (semantic + multi-hop)      │
└─────────────────────────────────────┘
    ↓
Reranker (RRF + Cross-encoder)
    ↓
Retrieval Grader (quality check)
    ↓
┌─────────────────────────────────────┐
│   If Quality Low:                    │
│   → Corrective RAG                   │
│   → Iterative Retrieval              │
└─────────────────────────────────────┘
    ↓
Enhanced Synthesis (with ground truth)
    ↓
Quality Check (citation verification)
    ↓
Final Answer
```

---

## Part 7: Specific Implementation Details

### 7.1 Query Planner Implementation

```python
# core_engine/reasoning/query_planner.py

class QueryPlanner:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def plan(self, query: str) -> Dict[str, Any]:
        """Analyze query and create retrieval plan."""
        prompt = f"""
        Analyze this query and create a retrieval plan:
        Query: {query}
        
        Determine:
        1. Intent type (definition, comparison, causal, multi_entity, etc.)
        2. Entities mentioned
        3. Relationships needed
        4. Sub-queries if complex
        5. Complexity level
        
        Return JSON with structure:
        {{
            "intent": "...",
            "entities": [...],
            "relationships": [...],
            "sub_queries": [...],
            "complexity": "...",
            "kg_query_type": "..."
        }}
        """
        # LLM call to generate plan
        return plan
```

---

### 7.2 Reranker Implementation

```python
# core_engine/reasoning/reranker.py

class Reranker:
    def __init__(self):
        # Initialize cross-encoder model if available
        pass
    
    def reciprocal_rank_fusion(
        self, 
        result_lists: List[List[Dict]], 
        k: int = 60
    ) -> List[Dict]:
        """Combine multiple ranked lists using RRF."""
        scores = {}
        for result_list in result_lists:
            for rank, result in enumerate(result_list, 1):
                result_id = result.get("id") or hash(result.get("text", ""))
                if result_id not in scores:
                    scores[result_id] = {"result": result, "rrf_score": 0.0}
                scores[result_id]["rrf_score"] += 1.0 / (k + rank)
        
        reranked = sorted(
            scores.values(), 
            key=lambda x: x["rrf_score"], 
            reverse=True
        )
        return [item["result"] for item in reranked]
    
    def cross_encoder_rerank(
        self, 
        query: str, 
        results: List[Dict]
    ) -> List[Dict]:
        """Rerank using cross-encoder model."""
        # Score each (query, result) pair
        # Reorder by scores
        pass
```

---

### 7.3 Enhanced KG Querying

```python
# core_engine/reasoning/kg_query_optimizer.py

class KGQueryOptimizer:
    def __init__(self, neo4j_client, embed_client):
        self.neo4j = neo4j_client
        self.embed = embed_client
    
    def semantic_search(self, query: str, top_k: int = 10):
        """Semantic KG search using embeddings."""
        query_embedding = self.embed.create(query)
        
        cypher = """
        MATCH (c:Concept)
        WHERE c.workspace_id = $workspace_id
          AND c.embedding IS NOT NULL
        WITH c, 
             cosineSimilarity(c.embedding, $query_embedding) as similarity
        WHERE similarity > 0.7
        RETURN c, similarity
        ORDER BY similarity DESC
        LIMIT $top_k
        """
        return self.neo4j.execute_read(cypher, {...})
    
    def multi_hop_query(
        self, 
        start_entity: str, 
        relationship_types: List[str],
        max_hops: int = 3
    ):
        """Multi-hop relationship traversal."""
        cypher = f"""
        MATCH path = (start:Concept)-[*1..{max_hops}]->(end:Concept)
        WHERE start.name CONTAINS $start_entity
          AND ALL(r IN relationships(path) WHERE type(r) IN $rel_types)
        RETURN path, length(path) as hops
        ORDER BY hops, relevance_score
        """
        return self.neo4j.execute_read(cypher, {...})
    
    def cross_episode_query(
        self, 
        concept_name: str,
        min_episodes: int = 2
    ):
        """Find concepts appearing across multiple episodes."""
        cypher = """
        MATCH (c:Concept)
        WHERE c.workspace_id = $workspace_id
          AND toLower(c.name) CONTAINS toLower($concept_name)
          AND size(c.episode_ids) >= $min_episodes
        RETURN c, 
               c.episode_ids as episodes,
               size(c.episode_ids) as episode_count
        ORDER BY episode_count DESC
        """
        return self.neo4j.execute_read(cypher, {...})
```

---

### 7.4 Enhanced Source Extraction

```python
# core_engine/reasoning/agent.py

def _extract_sources_enhanced(
    self,
    rag_results: List[Dict],
    kg_results: List[Dict]
) -> List[Dict]:
    """Extract sources with full ground truth metadata."""
    sources = []
    
    # RAG sources
    for result in rag_results:
        metadata = result.get("metadata", {})
        source = {
            "type": "transcript",
            "episode_id": metadata.get("episode_id", "unknown"),
            "episode_name": self._format_episode_name(metadata.get("episode_id")),
            "speaker": metadata.get("speaker", "Unknown"),
            "timestamp": metadata.get("timestamp", ""),
            "text": result.get("text", "")[:500],
            "confidence": result.get("score", 0.0),
            "source_path": metadata.get("source_path", "")
        }
        sources.append(source)
    
    # KG sources
    for result in kg_results:
        metadata = result.get("metadata", {})
        source = {
            "type": "knowledge_graph",
            "concept": metadata.get("name", ""),
            "concept_id": metadata.get("id", ""),
            "description": metadata.get("description", ""),
            "episode_ids": metadata.get("episode_ids", []),
            "relationships": metadata.get("relationships_out", []),
            "confidence": result.get("score", 0.0)
        }
        sources.append(source)
    
    return sources
```

---

## Part 8: Evaluation Metrics

### 8.1 Retrieval Metrics

1. **Recall@K**: Percentage of relevant documents retrieved in top-K
2. **Precision@K**: Percentage of top-K results that are relevant
3. **MRR (Mean Reciprocal Rank)**: Average of 1/rank of first relevant result
4. **NDCG@K**: Normalized Discounted Cumulative Gain

### 8.2 Answer Quality Metrics

1. **Citation Accuracy**: % of citations that are correct
2. **Entity Coverage**: % of mentioned entities covered
3. **Hallucination Rate**: % of unsupported claims
4. **Completeness**: % of question aspects answered

### 8.3 Test Suite

Create test cases for:
- Simple queries
- Complex multi-entity queries
- Comparison queries
- Causal queries
- Cross-episode queries

---

## Part 9: Next Steps

### Immediate Actions (This Week)

1. ✅ Create this analysis document
2. ⏭️ Implement Query Planner module
3. ⏭️ Implement Reranker (RRF first)
4. ⏭️ Enhance KG querying with semantic search

### Short-term (Next 2 Weeks)

1. Implement Iterative Retrieval
2. Add Self-Grading
3. Enhance Entity Linking
4. Improve Ground Truth Display

### Medium-term (Next Month)

1. Implement Corrective RAG
2. Add Cross-Encoder Reranking
3. Multi-hop KG queries
4. Cross-episode optimization

---

## Conclusion

This plan provides a comprehensive roadmap to transform your retrieval system from basic to best-in-class. The key improvements are:

1. **Intelligent Query Understanding** (Planning, Expansion, Decomposition)
2. **Advanced Retrieval** (Iterative, Corrective, Self-Grading)
3. **Optimized KG Usage** (Semantic, Multi-hop, Cross-episode)
4. **Superior Reranking** (RRF, Cross-encoder)
5. **Enhanced Synthesis** (Quality checks, Ground truth)

**Expected Outcome**: Significantly improved accuracy for complex queries, better KG utilization, and more reliable answers with proper source attribution.
