"""
Query templates for common knowledge graph queries.
Pre-built Cypher queries for common use cases.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List


class QueryTemplates:
    """Pre-built query templates for common use cases."""

    @staticmethod
    def practices_optimizing_concept(concept_name: str, workspace_id: str) -> Dict[str, Any]:
        """
        Find practices that optimize a concept.

        Args:
            concept_name: Concept name
            workspace_id: Workspace ID

        Returns:
            Query dictionary with cypher and parameters
        """
        return {
            "cypher": """
            MATCH (p:Practice)-[r:OPTIMIZES]->(c)
            WHERE c.workspace_id = $workspace_id
              AND (c.name CONTAINS $concept_name OR c.id CONTAINS $concept_name)
            RETURN p.name as practice,
                   p.id as practice_id,
                   c.name as concept,
                   c.id as concept_id,
                   r.description as description,
                   r.confidence as confidence
            ORDER BY r.confidence DESC
            LIMIT 20
            """,
            "parameters": {
                "workspace_id": workspace_id,
                "concept_name": concept_name,
            },
        }

    @staticmethod
    def concepts_in_multiple_episodes(min_episodes: int = 2, workspace_id: str = "default") -> Dict[str, Any]:
        """
        Find concepts appearing in multiple episodes.

        Args:
            min_episodes: Minimum episodes
            workspace_id: Workspace ID

        Returns:
            Query dictionary
        """
        return {
            "cypher": """
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND c.episode_ids IS NOT NULL
              AND size(c.episode_ids) >= $min_episodes
            RETURN c.name as concept,
                   c.type as type,
                   size(c.episode_ids) as episode_count,
                   c.episode_ids as episode_ids
            ORDER BY episode_count DESC
            LIMIT 50
            """,
            "parameters": {
                "workspace_id": workspace_id,
                "min_episodes": min_episodes,
            },
        }

    @staticmethod
    def quotes_about_concept(concept_name: str, workspace_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Find quotes about a concept.

        Args:
            concept_name: Concept name
            workspace_id: Workspace ID
            limit: Result limit

        Returns:
            Query dictionary
        """
        return {
            "cypher": """
            MATCH (q:Quote)-[:ABOUT]->(c)
            WHERE c.workspace_id = $workspace_id
              AND (c.name CONTAINS $concept_name OR c.id CONTAINS $concept_name)
            RETURN q.text as quote,
                   q.speaker as speaker,
                   q.timestamp as timestamp,
                   q.episode_id as episode_id,
                   c.name as concept
            ORDER BY q.confidence DESC
            LIMIT $limit
            """,
            "parameters": {
                "workspace_id": workspace_id,
                "concept_name": concept_name,
                "limit": limit,
            },
        }

    @staticmethod
    def cross_episode_relationships(min_episodes: int = 2, workspace_id: str = "default") -> Dict[str, Any]:
        """
        Find relationships appearing across episodes.

        Args:
            min_episodes: Minimum episodes
            workspace_id: Workspace ID

        Returns:
            Query dictionary
        """
        return {
            "cypher": """
            MATCH (a)-[r]->(b)
            WHERE a.workspace_id = $workspace_id
              AND b.workspace_id = $workspace_id
              AND r.episode_ids IS NOT NULL
              AND size(r.episode_ids) >= $min_episodes
              AND type(r) <> 'CROSS_EPISODE'
            RETURN a.name as source,
                   b.name as target,
                   type(r) as relationship,
                   size(r.episode_ids) as episode_count,
                   r.description as description
            ORDER BY episode_count DESC
            LIMIT 50
            """,
            "parameters": {
                "workspace_id": workspace_id,
                "min_episodes": min_episodes,
            },
        }

    @staticmethod
    def path_between_concepts(
        source_id: str,
        target_id: str,
        max_hops: int = 5,
        workspace_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Find path between two concepts.

        Args:
            source_id: Source concept ID
            target_id: Target concept ID
            max_hops: Maximum hops
            workspace_id: Workspace ID

        Returns:
            Query dictionary
        """
        return {
            "cypher": f"""
            MATCH path = shortestPath((source)-[*1..{max_hops}]->(target))
            WHERE source.workspace_id = $workspace_id
              AND target.workspace_id = $workspace_id
              AND source.id = $source_id
              AND target.id = $target_id
            RETURN [node in nodes(path) | node.name] as path_nodes,
                   [rel in relationships(path) | type(rel)] as path_relationships,
                   length(path) as path_length
            LIMIT 10
            """,
            "parameters": {
                "workspace_id": workspace_id,
                "source_id": source_id,
                "target_id": target_id,
            },
        }

    @staticmethod
    def concepts_by_type(concept_type: str, workspace_id: str = "default", limit: int = 50) -> Dict[str, Any]:
        """
        Find concepts by type.

        Args:
            concept_type: Concept type (e.g., "Practice", "Principle")
            workspace_id: Workspace ID
            limit: Result limit

        Returns:
            Query dictionary
        """
        return {
            "cypher": f"""
            MATCH (c:{concept_type})
            WHERE c.workspace_id = $workspace_id
            RETURN c.name as name,
                   c.id as id,
                   c.description as description,
                   size(c.episode_ids) as episode_count
            ORDER BY episode_count DESC
            LIMIT $limit
            """,
            "parameters": {
                "workspace_id": workspace_id,
                "limit": limit,
            },
        }

    @staticmethod
    def speaker_quotes(speaker_name: str, workspace_id: str = "default", limit: int = 20) -> Dict[str, Any]:
        """
        Find quotes by speaker.

        Args:
            speaker_name: Speaker name
            workspace_id: Workspace ID
            limit: Result limit

        Returns:
            Query dictionary
        """
        return {
            "cypher": """
            MATCH (q:Quote)
            WHERE q.workspace_id = $workspace_id
              AND q.speaker CONTAINS $speaker_name
            RETURN q.text as quote,
                   q.speaker as speaker,
                   q.timestamp as timestamp,
                   q.episode_id as episode_id
            ORDER BY q.confidence DESC
            LIMIT $limit
            """,
            "parameters": {
                "workspace_id": workspace_id,
                "speaker_name": speaker_name,
                "limit": limit,
            },
        }

    @staticmethod
    def get_all_templates() -> List[str]:
        """
        Get list of all available template names.

        Returns:
            List of template method names
        """
        return [
            "practices_optimizing_concept",
            "concepts_in_multiple_episodes",
            "quotes_about_concept",
            "cross_episode_relationships",
            "path_between_concepts",
            "concepts_by_type",
            "speaker_quotes",
        ]

