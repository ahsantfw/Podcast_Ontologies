"""
Agent tools for querying the knowledge graph.
Provides tool functions for agent frameworks (LangChain, LangGraph).
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.reasoning.query_generator import QueryGenerator
from core_engine.reasoning.multi_hop import MultiHopReasoner
from core_engine.reasoning.hybrid_retriever import HybridRetriever
from core_engine.logging import get_logger


class KGTools:
    """Tools for agent frameworks to query the knowledge graph."""

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        workspace_id: Optional[str] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
    ):
        """
        Initialize KG tools.

        Args:
            neo4j_client: Neo4j client
            workspace_id: Workspace identifier
            hybrid_retriever: Optional hybrid retriever
        """
        self.client = neo4j_client
        self.workspace_id = workspace_id or "default"
        self.query_generator = QueryGenerator(neo4j_client, workspace_id=workspace_id)
        self.multi_hop = MultiHopReasoner(neo4j_client, workspace_id=workspace_id)
        self.hybrid_retriever = hybrid_retriever
        self.logger = get_logger(
            "core_engine.reasoning.agent_tools",
            workspace_id=self.workspace_id,
        )

    def search_concepts(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for concepts matching a query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching concepts
        """
        cypher = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (c.name CONTAINS $query 
               OR c.description CONTAINS $query
               OR toLower(c.name) CONTAINS toLower($query))
        RETURN c.name as name,
               c.type as type,
               c.description as description,
               c.id as id,
               size(c.episode_ids) as episode_count
        LIMIT $limit
        """
        
        results = self.query_generator.execute_query(
            cypher,
            {"query": query, "limit": limit},
        )
        
        return results

    def get_concept_details(
        self,
        concept_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a concept.

        Args:
            concept_id: Concept ID

        Returns:
            Concept details or None
        """
        cypher = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND c.id = $concept_id
        OPTIONAL MATCH (c)-[r]->(related)
        WHERE related.workspace_id = $workspace_id
        RETURN c.name as name,
               c.type as type,
               c.description as description,
               c.episode_ids as episode_ids,
               c.speakers as speakers,
               collect(DISTINCT {
                   relationship: type(r),
                   target: related.name,
                   target_id: related.id
               }) as relationships
        LIMIT 1
        """
        
        results = self.query_generator.execute_query(
            cypher,
            {"concept_id": concept_id},
        )
        
        return results[0] if results else None

    def find_related_concepts(
        self,
        concept_id: str,
        relationship_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Find concepts related to a given concept.

        Args:
            concept_id: Concept ID
            relationship_types: Optional list of relationship types
            limit: Maximum results

        Returns:
            List of related concepts
        """
        rel_filter = ""
        if relationship_types:
            rel_types_str = "|".join(relationship_types)
            rel_filter = f":{rel_types_str}"
        
        cypher = f"""
        MATCH (source)-[r{rel_filter}]->(target)
        WHERE source.workspace_id = $workspace_id
          AND target.workspace_id = $workspace_id
          AND source.id = $concept_id
        RETURN target.name as name,
               target.id as id,
               target.type as type,
               type(r) as relationship,
               r.description as description
        LIMIT $limit
        """
        
        results = self.query_generator.execute_query(
            cypher,
            {"concept_id": concept_id, "limit": limit},
        )
        
        return results

    def find_practices_for_outcome(
        self,
        outcome: str,
        max_hops: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find practices that lead to an outcome.

        Args:
            outcome: Outcome concept name or ID
            max_hops: Maximum hops

        Returns:
            List of practices
        """
        return self.multi_hop.find_practices_for_outcome(outcome, max_hops)

    def get_quotes_about(
        self,
        concept_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get quotes about a concept.

        Args:
            concept_id: Concept ID
            limit: Maximum results

        Returns:
            List of quotes
        """
        cypher = """
        MATCH (q:Quote)-[:ABOUT]->(c)
        WHERE c.workspace_id = $workspace_id
          AND c.id = $concept_id
        RETURN q.text as text,
               q.speaker as speaker,
               q.timestamp as timestamp,
               q.episode_id as episode_id
        LIMIT $limit
        """
        
        results = self.query_generator.execute_query(
            cypher,
            {"concept_id": concept_id, "limit": limit},
        )
        
        return results

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search using vector + graph.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of search results
        """
        if not self.hybrid_retriever:
            # Fallback to graph search only
            return self.search_concepts(query, limit=top_k)
        
        return self.hybrid_retriever.retrieve(query, top_k=top_k)


def create_kg_tools(
    neo4j_client: Neo4jClient,
    workspace_id: Optional[str] = None,
    hybrid_retriever: Optional[HybridRetriever] = None,
) -> KGTools:
    """
    Create KG tools (convenience function).

    Args:
        neo4j_client: Neo4j client
        workspace_id: Workspace identifier
        hybrid_retriever: Optional hybrid retriever

    Returns:
        KGTools instance
    """
    return KGTools(
        neo4j_client=neo4j_client,
        workspace_id=workspace_id,
        hybrid_retriever=hybrid_retriever,
    )


# LangChain tool definitions
def get_langchain_tools(kg_tools: KGTools) -> List[Any]:
    """
    Get LangChain tool definitions.

    Args:
        kg_tools: KGTools instance

    Returns:
        List of LangChain tools
    """
    try:
        from langchain.tools import tool
        
        @tool
        def search_concepts(query: str) -> str:
            """Search for concepts in the knowledge graph."""
            results = kg_tools.search_concepts(query, limit=5)
            if not results:
                return "No concepts found."
            return "\n".join([
                f"- {r['name']} ({r['type']}): {r.get('description', '')[:100]}"
                for r in results
            ])
        
        @tool
        def get_concept_details(concept_id: str) -> str:
            """Get detailed information about a concept."""
            details = kg_tools.get_concept_details(concept_id)
            if not details:
                return f"Concept {concept_id} not found."
            return f"{details['name']} ({details['type']}): {details.get('description', '')}"
        
        @tool
        def find_related_concepts(concept_id: str) -> str:
            """Find concepts related to a given concept."""
            results = kg_tools.find_related_concepts(concept_id, limit=5)
            if not results:
                return f"No related concepts found for {concept_id}."
            return "\n".join([
                f"- {r['name']} ({r['relationship']})"
                for r in results
            ])
        
        return [search_concepts, get_concept_details, find_related_concepts]
    
    except ImportError:
        return []

