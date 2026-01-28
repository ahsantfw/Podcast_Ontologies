# Quick Start: Critical Retrieval Improvements

## Priority 1: Query Planner & Decomposition (Start Here)

**Why**: Complex questions fail because we don't decompose them.

**File**: `core_engine/reasoning/query_planner.py`

```python
"""
Query Planner - Decompose complex queries into sub-queries.
"""
from typing import Dict, Any, List
from core_engine.logging import get_logger
from openai import OpenAI
import json

class QueryPlanner:
    def __init__(self, openai_client: OpenAI):
        self.llm = openai_client
        self.logger = get_logger(__name__)
    
    def plan_query(self, query: str) -> Dict[str, Any]:
        """Analyze query and create retrieval plan."""
        system_prompt = """You are a query analysis expert. Analyze user queries and determine:
1. Query intent (definition, comparison, causal, multi_entity, etc.)
2. Entities mentioned
3. Relationships needed
4. Sub-queries if complex
5. Complexity level

Return JSON only."""
        
        user_prompt = f"Analyze this query: {query}"
        
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        plan = json.loads(response.choices[0].message.content)
        return plan
    
    def decompose_complex_query(self, query: str) -> List[str]:
        """Break complex query into sub-queries."""
        plan = self.plan_query(query)
        
        if plan.get("complexity") == "complex" and plan.get("sub_queries"):
            return plan["sub_queries"]
        
        return [query]  # Simple query, no decomposition needed
```

---

## Priority 2: Reranker (RRF Implementation)

**Why**: Current fusion is too simple. RRF improves ranking significantly.

**File**: `core_engine/reasoning/reranker.py`

```python
"""
Reranker - Advanced ranking algorithms.
"""
from typing import List, Dict, Any
from collections import defaultdict

class Reranker:
    def reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine multiple ranked lists using Reciprocal Rank Fusion.
        
        Args:
            result_lists: List of ranked result lists (e.g., [rag_results, kg_results])
            k: RRF constant (typically 60)
        
        Returns:
            Reranked and fused results
        """
        scores = defaultdict(lambda: {"result": None, "rrf_score": 0.0, "seen_in": []})
        
        for rank, result_list in enumerate(result_lists):
            for position, result in enumerate(result_list, 1):
                # Create unique ID for result
                result_id = self._get_result_id(result)
                
                if result_id not in scores:
                    scores[result_id]["result"] = result
                
                # RRF formula: 1 / (k + rank)
                rrf_score = 1.0 / (k + position)
                scores[result_id]["rrf_score"] += rrf_score
                scores[result_id]["seen_in"].append(rank)
        
        # Sort by RRF score
        reranked = sorted(
            scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        return [item["result"] for item in reranked]
    
    def _get_result_id(self, result: Dict[str, Any]) -> str:
        """Generate unique ID for result."""
        # Try multiple fields for uniqueness
        if "id" in result:
            return str(result["id"])
        elif "metadata" in result and "id" in result["metadata"]:
            return str(result["metadata"]["id"])
        else:
            # Use text hash as fallback
            text = result.get("text", "")[:100]
            return str(hash(text))
```

---

## Priority 3: Enhanced KG Querying

**Why**: Current KG queries are too simple. Need semantic + multi-hop.

**File**: `core_engine/reasoning/kg_query_optimizer.py`

```python
"""
KG Query Optimizer - Advanced knowledge graph querying.
"""
from typing import List, Dict, Any, Optional
from core_engine.kg.neo4j_client import Neo4jClient
from openai import OpenAI

class KGQueryOptimizer:
    def __init__(self, neo4j_client: Neo4jClient, openai_client: OpenAI):
        self.neo4j = neo4j_client
        self.llm = openai_client
    
    def multi_hop_query(
        self,
        query: str,
        start_entities: List[str],
        relationship_types: Optional[List[str]] = None,
        max_hops: int = 3,
        workspace_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Multi-hop relationship traversal.
        
        Example: "What practices lead to outcomes that Phil Jackson uses?"
        - Find Phil Jackson concepts
        - Traverse to practices
        - Traverse to outcomes
        """
        rel_filter = ""
        if relationship_types:
            rel_types_str = ", ".join([f"'{rt}'" for rt in relationship_types])
            rel_filter = f"AND ALL(r IN relationships(path) WHERE type(r) IN [{rel_types_str}])"
        
        cypher = f"""
        MATCH path = (start:Concept)-[*1..{max_hops}]->(end:Concept)
        WHERE start.workspace_id = $workspace_id
          AND ANY(entity IN $start_entities WHERE toLower(start.name) CONTAINS toLower(entity))
          AND end.workspace_id = $workspace_id
          {rel_filter}
        WITH path, start, end, length(path) as hops
        RETURN DISTINCT
            end.name as concept,
            end.description as description,
            end.id as id,
            end.episode_ids as episode_ids,
            hops,
            [r IN relationships(path) | type(r)] as relationship_path
        ORDER BY hops ASC, end.name
        LIMIT 20
        """
        
        results = self.neo4j.execute_read(
            cypher,
            {
                "workspace_id": workspace_id,
                "start_entities": start_entities,
            }
        )
        
        return results
    
    def cross_episode_query(
        self,
        concept_name: str,
        min_episodes: int = 2,
        workspace_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Find concepts appearing across multiple episodes."""
        cypher = """
        MATCH (c:Concept)
        WHERE c.workspace_id = $workspace_id
          AND (
            toLower(c.name) CONTAINS toLower($concept_name)
            OR toLower(c.description) CONTAINS toLower($concept_name)
          )
          AND size(c.episode_ids) >= $min_episodes
        WITH c, size(c.episode_ids) as episode_count
        OPTIONAL MATCH (c)-[r]->(related:Concept)
        WHERE related.workspace_id = $workspace_id
        RETURN c.name as concept,
               c.description as description,
               c.id as id,
               c.episode_ids as episodes,
               episode_count,
               collect(DISTINCT {rel: type(r), target: related.name})[0..5] as relationships
        ORDER BY episode_count DESC, c.name
        LIMIT 10
        """
        
        results = self.neo4j.execute_read(
            cypher,
            {
                "workspace_id": workspace_id,
                "concept_name": concept_name,
                "min_episodes": min_episodes
            }
        )
        
        return results
    
    def entity_centric_query(
        self,
        entity_name: str,
        relationship_direction: str = "both",  # "out", "in", "both"
        workspace_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get all information about an entity and its relationships.
        
        Returns entity with all connected concepts.
        """
        if relationship_direction == "both":
            match_clause = """
            OPTIONAL MATCH (entity)-[r_out]->(outgoing:Concept)
            WHERE outgoing.workspace_id = $workspace_id
            OPTIONAL MATCH (incoming:Concept)-[r_in]->(entity)
            WHERE incoming.workspace_id = $workspace_id
            """
            return_clause = """
            collect(DISTINCT {rel: type(r_out), target: outgoing.name, desc: r_out.description}) as outgoing_rels,
            collect(DISTINCT {rel: type(r_in), source: incoming.name, desc: r_in.description}) as incoming_rels
            """
        elif relationship_direction == "out":
            match_clause = """
            OPTIONAL MATCH (entity)-[r_out]->(outgoing:Concept)
            WHERE outgoing.workspace_id = $workspace_id
            """
            return_clause = """
            collect(DISTINCT {rel: type(r_out), target: outgoing.name, desc: r_out.description}) as outgoing_rels,
            [] as incoming_rels
            """
        else:  # "in"
            match_clause = """
            OPTIONAL MATCH (incoming:Concept)-[r_in]->(entity)
            WHERE incoming.workspace_id = $workspace_id
            """
            return_clause = """
            [] as outgoing_rels,
            collect(DISTINCT {rel: type(r_in), source: incoming.name, desc: r_in.description}) as incoming_rels
            """
        
        cypher = f"""
        MATCH (entity:Concept)
        WHERE entity.workspace_id = $workspace_id
          AND toLower(entity.name) CONTAINS toLower($entity_name)
        {match_clause}
        RETURN entity.name as name,
               entity.description as description,
               entity.id as id,
               entity.episode_ids as episodes,
               entity.type as type,
               {return_clause}
        LIMIT 1
        """
        
        results = self.neo4j.execute_read(
            cypher,
            {
                "workspace_id": workspace_id,
                "entity_name": entity_name
            }
        )
        
        return results[0] if results else {}
```

---

## Priority 4: Integration into Agent

**Update**: `core_engine/reasoning/agent.py`

```python
# Add imports
from core_engine.reasoning.query_planner import QueryPlanner
from core_engine.reasoning.reranker import Reranker
from core_engine.reasoning.kg_query_optimizer import KGQueryOptimizer

class PodcastAgent:
    def __init__(self, ...):
        # ... existing init ...
        
        # Add new components
        self.query_planner = QueryPlanner(self.openai_client)
        self.reranker = Reranker()
        self.kg_optimizer = KGQueryOptimizer(self.neo4j_client, self.openai_client)
    
    def _handle_knowledge_query(self, query: str, ...):
        # 1. Plan query
        plan = self.query_planner.plan_query(query)
        
        # 2. Decompose if complex
        sub_queries = self.query_planner.decompose_complex_query(query)
        
        # 3. Retrieve for each sub-query
        all_rag_results = []
        all_kg_results = []
        
        for sub_query in sub_queries:
            rag_res = self.hybrid_retriever.retrieve(sub_query, use_vector=True, use_graph=False)
            kg_res = self.kg_optimizer.multi_hop_query(sub_query, plan.get("entities", []))
            all_rag_results.extend(rag_res)
            all_kg_results.extend(kg_res)
        
        # 4. Rerank using RRF
        reranked_results = self.reranker.reciprocal_rank_fusion([
            all_rag_results,
            all_kg_results
        ])
        
        # 5. Continue with synthesis...
```

---

## Next Steps

1. **Implement Query Planner** (2-3 hours)
2. **Implement Reranker** (1-2 hours)
3. **Enhance KG Querying** (3-4 hours)
4. **Integrate into Agent** (2-3 hours)
5. **Test with complex queries** (ongoing)

**Total Time**: ~8-12 hours for basic implementation

**Expected Improvement**: 
- Better handling of complex queries
- Improved ranking accuracy
- Better KG utilization
