"""
Multi-hop reasoning and path traversal.
Finds paths between concepts and enables complex reasoning queries.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger


class MultiHopReasoner:
    """Multi-hop reasoning over the knowledge graph."""

    def __init__(
        self,
        client: Neo4jClient,
        workspace_id: Optional[str] = None,
        max_hops: int = 5,
    ):
        """
        Initialize multi-hop reasoner.

        Args:
            client: Neo4j client
            workspace_id: Workspace identifier
            max_hops: Maximum number of hops for path finding
        """
        self.client = client
        self.workspace_id = workspace_id or "default"
        self.max_hops = max_hops
        self.logger = get_logger(
            "core_engine.reasoning.multi_hop",
            workspace_id=self.workspace_id,
        )

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_hops: Optional[int] = None,
        relationship_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find paths between two concepts.

        Args:
            source_id: Source concept ID
            target_id: Target concept ID
            max_hops: Maximum hops (default: self.max_hops)
            relationship_types: Optional list of relationship types to follow

        Returns:
            List of paths with nodes and relationships
        """
        max_hops = max_hops or self.max_hops
        
        # Build relationship filter
        rel_filter = ""
        if relationship_types:
            rel_types_str = "|".join(relationship_types)
            rel_filter = f":{rel_types_str}"
        
        query = f"""
        MATCH path = shortestPath((source)-[*1..{max_hops}{rel_filter}]->(target))
        WHERE source.workspace_id = $workspace_id
          AND target.workspace_id = $workspace_id
          AND source.id = $source_id
          AND target.id = $target_id
        RETURN path,
               [node in nodes(path) | node.name] as node_names,
               [rel in relationships(path) | type(rel)] as relationship_types,
               length(path) as path_length
        LIMIT 10
        """
        
        results = self.client.execute_read(
            query,
            {
                "workspace_id": self.workspace_id,
                "source_id": source_id,
                "target_id": target_id,
            },
        )
        
        paths = []
        for result in results:
            paths.append({
                "node_names": result["node_names"],
                "relationship_types": result["relationship_types"],
                "path_length": result["path_length"],
            })
        
        self.logger.info(
            "paths_found",
            extra={
                "context": {
                    "source_id": source_id,
                    "target_id": target_id,
                    "path_count": len(paths),
                }
            },
        )
        
        return paths

    def find_concepts_influencing(
        self,
        target_concept: str,
        max_hops: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Find concepts that influence a target concept (directly or indirectly).

        Args:
            target_concept: Target concept name or ID
            max_hops: Maximum hops to traverse

        Returns:
            List of influencing concepts
        """
        query = f"""
        MATCH (target)
        WHERE target.workspace_id = $workspace_id
          AND (target.name CONTAINS $target_concept OR target.id CONTAINS $target_concept)
        MATCH path = (source)-[*1..{max_hops}]->(target)
        WHERE source.workspace_id = $workspace_id
          AND any(rel in relationships(path) WHERE type(rel) IN ['INFLUENCES', 'CAUSES', 'OPTIMIZES', 'ENABLES'])
        RETURN DISTINCT source.name as concept_name,
               source.id as concept_id,
               source.type as concept_type,
               length(path) as hop_distance
        ORDER BY hop_distance, concept_name
        LIMIT 50
        """
        
        results = self.client.execute_read(
            query,
            {
                "workspace_id": self.workspace_id,
                "target_concept": target_concept,
            },
        )
        
        return [
            {
                "concept_name": r["concept_name"],
                "concept_id": r["concept_id"],
                "concept_type": r["concept_type"],
                "hop_distance": r["hop_distance"],
            }
            for r in results
        ]

    def find_practices_for_outcome(
        self,
        outcome: str,
        max_hops: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find practices that lead to a specific outcome (multi-hop).

        Args:
            outcome: Outcome concept name or ID
            max_hops: Maximum hops to traverse

        Returns:
            List of practices with paths
        """
        query = f"""
        MATCH (outcome)
        WHERE outcome.workspace_id = $workspace_id
          AND (outcome.name CONTAINS $outcome OR outcome.id CONTAINS $outcome)
        MATCH path = (practice:Practice)-[*1..{max_hops}]->(outcome)
        WHERE practice.workspace_id = $workspace_id
          AND any(rel in relationships(path) WHERE type(rel) IN ['LEADS_TO', 'CAUSES', 'OPTIMIZES', 'ENABLES'])
        RETURN DISTINCT practice.name as practice_name,
               practice.id as practice_id,
               [node in nodes(path) | node.name] as path_nodes,
               [rel in relationships(path) | type(rel)] as path_relationships,
               length(path) as path_length
        ORDER BY path_length, practice_name
        LIMIT 30
        """
        
        results = self.client.execute_read(
            query,
            {
                "workspace_id": self.workspace_id,
                "outcome": outcome,
            },
        )
        
        return [
            {
                "practice_name": r["practice_name"],
                "practice_id": r["practice_id"],
                "path_nodes": r["path_nodes"],
                "path_relationships": r["path_relationships"],
                "path_length": r["path_length"],
            }
            for r in results
        ]

    def reason_about_question(
        self,
        question: str,
        max_hops: int = 3,
    ) -> Dict[str, Any]:
        """
        Reason about a question using multi-hop traversal.

        Args:
            question: Natural language question
            max_hops: Maximum hops for reasoning

        Returns:
            Reasoning results with paths and concepts
        """
        # Extract key concepts from question (simple heuristic)
        question_lower = question.lower()
        
        # Pattern: "What practices optimize X?"
        if "practice" in question_lower and "optimize" in question_lower:
            target = self._extract_target(question)
            return {
                "type": "practices_for_outcome",
                "target": target,
                "results": self.find_practices_for_outcome(target, max_hops),
            }
        
        # Pattern: "What influences X?"
        if "influence" in question_lower:
            target = self._extract_target(question)
            return {
                "type": "concepts_influencing",
                "target": target,
                "results": self.find_concepts_influencing(target, max_hops),
            }
        
        # Default: return empty
        return {
            "type": "unknown",
            "results": [],
        }

    def _extract_target(self, question: str) -> str:
        """
        Extract target concept from question.

        Args:
            question: Natural language question

        Returns:
            Extracted target concept
        """
        # Simple extraction - can be improved
        words = question.split()
        stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "practices", "optimize", "influence"}
        concepts = [w for w in words if w.lower() not in stop_words]
        return " ".join(concepts[-2:])  # Last 2 words

    def get_concept_neighborhood(
        self,
        concept_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Get neighborhood around a concept (all connected concepts).

        Args:
            concept_id: Concept ID
            depth: Depth of neighborhood

        Returns:
            Neighborhood graph structure
        """
        query = f"""
        MATCH (center)
        WHERE center.workspace_id = $workspace_id
          AND center.id = $concept_id
        MATCH path = (center)-[*1..{depth}]-(neighbor)
        WHERE neighbor.workspace_id = $workspace_id
        WITH DISTINCT neighbor, length(path) as distance
        RETURN neighbor.name as name,
               neighbor.id as id,
               neighbor.type as type,
               distance
        ORDER BY distance, name
        LIMIT 100
        """
        
        results = self.client.execute_read(
            query,
            {
                "workspace_id": self.workspace_id,
                "concept_id": concept_id,
            },
        )
        
        return {
            "center": concept_id,
            "neighbors": [
                {
                    "name": r["name"],
                    "id": r["id"],
                    "type": r["type"],
                    "distance": r["distance"],
                }
                for r in results
            ],
        }


def create_multi_hop_reasoner(
    client: Neo4jClient,
    workspace_id: Optional[str] = None,
) -> MultiHopReasoner:
    """
    Create multi-hop reasoner (convenience function).

    Args:
        client: Neo4j client
        workspace_id: Workspace identifier

    Returns:
        MultiHopReasoner instance
    """
    return MultiHopReasoner(client, workspace_id=workspace_id)

