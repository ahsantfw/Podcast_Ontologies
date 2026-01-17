"""
Cross-episode linking and pattern detection.
Detects concepts and relationships that appear across multiple episodes
and creates CROSS_EPISODE relationships to identify recurring themes.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.kg.schema import RelationshipTypes
from core_engine.logging import get_logger


class CrossEpisodeLinker:
    """Detect and link concepts/relationships across episodes."""

    def __init__(self, client: Neo4jClient, workspace_id: Optional[str] = None):
        """
        Initialize cross-episode linker.

        Args:
            client: Neo4j client instance
            workspace_id: Workspace identifier
        """
        self.client = client
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger(
            "core_engine.kg.cross_episode",
            workspace_id=self.workspace_id,
        )

    def find_cross_episode_concepts(
        self, min_episodes: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find concepts that appear in multiple episodes.

        Args:
            min_episodes: Minimum number of episodes a concept must appear in

        Returns:
            List of concept dictionaries with episode counts
        """
        self.logger.info(
            "finding_cross_episode_concepts",
            extra={"context": {"min_episodes": min_episodes}},
        )

        # Query to find concepts with multiple episode_ids
        # We check all concept-like labels
        query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND c.episode_ids IS NOT NULL
          AND size(c.episode_ids) >= $min_episodes
          AND (c:Concept OR c:Practice OR c:CognitiveState OR c:BehavioralPattern 
               OR c:Principle OR c:Outcome OR c:Causality OR c:Person 
               OR c:Place OR c:Organization OR c:Event)
        RETURN c.id as id,
               c.name as name,
               c.type as type,
               c.description as description,
               c.episode_ids as episode_ids,
               size(c.episode_ids) as episode_count,
               c.source_paths as source_paths,
               c.speakers as speakers,
               c.confidences as confidences
        ORDER BY episode_count DESC
        """

        results = self.client.execute_read(
            query, {"workspace_id": self.workspace_id, "min_episodes": min_episodes}
        )

        concepts = []
        for record in results:
            concepts.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "description": record.get("description", ""),
                    "episode_ids": record["episode_ids"],
                    "episode_count": record["episode_count"],
                    "source_paths": record.get("source_paths", []),
                    "speakers": record.get("speakers", []),
                    "avg_confidence": (
                        sum(record.get("confidences", [1.0])) / len(record.get("confidences", [1.0]))
                        if record.get("confidences")
                        else 1.0
                    ),
                }
            )

        self.logger.info(
            "cross_episode_concepts_found",
            extra={"context": {"count": len(concepts)}},
        )

        return concepts

    def find_cross_episode_relationships(
        self, min_episodes: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find relationships that appear across multiple episodes.

        Args:
            min_episodes: Minimum number of episodes a relationship must appear in

        Returns:
            List of relationship dictionaries with episode counts
        """
        self.logger.info(
            "finding_cross_episode_relationships",
            extra={"context": {"min_episodes": min_episodes}},
        )

        # Query to find relationships with multiple episode_ids
        # Note: Relationships don't have workspace_id, but nodes do
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.workspace_id = $workspace_id
          AND b.workspace_id = $workspace_id
          AND r.episode_ids IS NOT NULL
          AND size(r.episode_ids) >= $min_episodes
          AND type(r) <> $cross_episode_type
        RETURN a.id as source_id,
               a.name as source_name,
               b.id as target_id,
               b.name as target_name,
               type(r) as rel_type,
               r.description as description,
               r.episode_ids as episode_ids,
               size(r.episode_ids) as episode_count,
               r.confidences as confidences
        ORDER BY episode_count DESC
        LIMIT 1000
        """

        results = self.client.execute_read(
            query,
            {
                "workspace_id": self.workspace_id,
                "min_episodes": min_episodes,
                "cross_episode_type": RelationshipTypes.CROSS_EPISODE,
            },
        )

        relationships = []
        for record in results:
            relationships.append(
                {
                    "source_id": record["source_id"],
                    "source_name": record["source_name"],
                    "target_id": record["target_id"],
                    "target_name": record["target_name"],
                    "type": record["rel_type"],
                    "description": record.get("description", ""),
                    "episode_ids": record["episode_ids"],
                    "episode_count": record["episode_count"],
                    "avg_confidence": (
                        sum(record.get("confidences", [1.0])) / len(record.get("confidences", [1.0]))
                        if record.get("confidences")
                        else 1.0
                    ),
                }
            )

        self.logger.info(
            "cross_episode_relationships_found",
            extra={"context": {"count": len(relationships)}},
        )

        return relationships

    def find_co_occurring_concepts(
        self, min_episodes: int = 2, min_co_occurrences: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find concepts that co-occur in the same episodes.

        Args:
            min_episodes: Minimum episodes each concept must appear in
            min_co_occurrences: Minimum episodes where concepts co-occur

        Returns:
            List of co-occurrence dictionaries
        """
        self.logger.info(
            "finding_co_occurring_concepts",
            extra={
                "context": {
                    "min_episodes": min_episodes,
                    "min_co_occurrences": min_co_occurrences,
                }
            },
        )

        # Find concepts that appear together in multiple episodes
        query = """
        MATCH (a), (b)
        WHERE a.workspace_id = $workspace_id
          AND b.workspace_id = $workspace_id
          AND a.id < b.id  // Avoid duplicates and self-loops
          AND a.episode_ids IS NOT NULL
          AND b.episode_ids IS NOT NULL
          AND size(a.episode_ids) >= $min_episodes
          AND size(b.episode_ids) >= $min_episodes
          AND (a:Concept OR a:Practice OR a:CognitiveState OR a:BehavioralPattern 
               OR a:Principle OR a:Outcome OR a:Causality OR a:Person 
               OR a:Place OR a:Organization OR a:Event)
          AND (b:Concept OR b:Practice OR b:CognitiveState OR b:BehavioralPattern 
               OR b:Principle OR b:Outcome OR b:Causality OR b:Person 
               OR b:Place OR b:Organization OR b:Event)
        WITH a, b, 
             [ep_id IN a.episode_ids WHERE ep_id IN b.episode_ids] as shared_episodes
        WHERE size(shared_episodes) >= $min_co_occurrences
        RETURN a.id as source_id,
               a.name as source_name,
               a.type as source_type,
               b.id as target_id,
               b.name as target_name,
               b.type as target_type,
               shared_episodes as shared_episode_ids,
               size(shared_episodes) as co_occurrence_count,
               a.episode_ids as source_episodes,
               b.episode_ids as target_episodes
        ORDER BY co_occurrence_count DESC
        LIMIT 1000  // Limit to top 1000 co-occurrences
        """

        results = self.client.execute_read(
            query,
            {
                "workspace_id": self.workspace_id,
                "min_episodes": min_episodes,
                "min_co_occurrences": min_co_occurrences,
            },
        )

        co_occurrences = []
        for record in results:
            co_occurrences.append(
                {
                    "source_id": record["source_id"],
                    "source_name": record["source_name"],
                    "source_type": record["source_type"],
                    "target_id": record["target_id"],
                    "target_name": record["target_name"],
                    "target_type": record["target_type"],
                    "shared_episode_ids": record["shared_episode_ids"],
                    "co_occurrence_count": record["co_occurrence_count"],
                    "source_episode_count": len(record["source_episodes"]),
                    "target_episode_count": len(record["target_episodes"]),
                }
            )

        self.logger.info(
            "co_occurring_concepts_found",
            extra={"context": {"count": len(co_occurrences)}},
        )

        return co_occurrences

    def create_cross_episode_links(
        self,
        min_episodes: int = 2,
        min_co_occurrences: int = 2,
        min_confidence: float = 0.5,
    ) -> Dict[str, int]:
        """
        Create CROSS_EPISODE relationships between co-occurring concepts.

        Args:
            min_episodes: Minimum episodes each concept must appear in
            min_co_occurrences: Minimum episodes where concepts co-occur
            min_confidence: Minimum confidence threshold

        Returns:
            Dictionary with counts of created relationships
        """
        self.logger.info(
            "creating_cross_episode_links",
            extra={
                "context": {
                    "min_episodes": min_episodes,
                    "min_co_occurrences": min_co_occurrences,
                    "min_confidence": min_confidence,
                }
            },
        )

        # Find co-occurring concepts
        co_occurrences = self.find_co_occurring_concepts(
            min_episodes=min_episodes, min_co_occurrences=min_co_occurrences
        )

        if not co_occurrences:
            self.logger.info("no_co_occurrences_found")
            return {"created": 0, "skipped": 0}

        # Create CROSS_EPISODE relationships
        queries = []
        created = 0
        skipped = 0

        for co_occ in co_occurrences:
            source_id = co_occ["source_id"]
            target_id = co_occ["target_id"]
            shared_episodes = co_occ["shared_episode_ids"]
            co_occurrence_count = co_occ["co_occurrence_count"]

            # Calculate confidence based on co-occurrence frequency
            # Higher co-occurrence = higher confidence
            confidence = min(1.0, co_occurrence_count / 10.0)  # Cap at 1.0

            if confidence < min_confidence:
                skipped += 1
                continue

            # Create CROSS_EPISODE relationship
            query = f"""
            MATCH (a {{id: $source_id, workspace_id: $workspace_id}})
            MATCH (b {{id: $target_id, workspace_id: $workspace_id}})
            MERGE (a)-[r:{RelationshipTypes.CROSS_EPISODE}]->(b)
            ON CREATE SET
                r.episode_ids = $shared_episode_ids,
                r.co_occurrence_count = $co_occurrence_count,
                r.confidence = $confidence,
                r.description = $description,
                r.workspace_id = $workspace_id,
                r.created_at = datetime()
            ON MATCH SET
                r.episode_ids = CASE 
                    WHEN $shared_episode_ids IS NOT NULL THEN 
                        [ep IN r.episode_ids WHERE ep IN $shared_episode_ids] + 
                        [ep IN $shared_episode_ids WHERE NOT ep IN r.episode_ids]
                    ELSE r.episode_ids 
                END,
                r.co_occurrence_count = $co_occurrence_count,
                r.confidence = $confidence,
                r.workspace_id = COALESCE(r.workspace_id, $workspace_id),
                r.updated_at = datetime()
            RETURN r
            """

            description = (
                f"Co-occurs in {co_occurrence_count} episode(s): "
                f"{co_occ['source_name']} and {co_occ['target_name']}"
            )

            queries.append(
                (
                    query,
                    {
                        "source_id": source_id,
                        "target_id": target_id,
                        "workspace_id": self.workspace_id,
                        "shared_episode_ids": shared_episodes,
                        "co_occurrence_count": co_occurrence_count,
                        "confidence": confidence,
                        "description": description,
                    },
                )
            )

        # Execute in batches
        batch_size = 100
        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            self.client.execute_write_batch(batch)
            created += len(batch)

        self.logger.info(
            "cross_episode_links_created",
            extra={"context": {"created": created, "skipped": skipped}},
        )

        return {"created": created, "skipped": skipped}

    def get_recurring_themes(
        self, min_episodes: int = 3, top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Identify recurring themes (concepts appearing in many episodes).

        Args:
            min_episodes: Minimum episodes for a theme
            top_n: Number of top themes to return

        Returns:
            List of theme dictionaries
        """
        self.logger.info(
            "finding_recurring_themes",
            extra={"context": {"min_episodes": min_episodes, "top_n": top_n}},
        )

        concepts = self.find_cross_episode_concepts(min_episodes=min_episodes)
        concepts.sort(key=lambda x: x["episode_count"], reverse=True)

        themes = []
        for concept in concepts[:top_n]:
            themes.append(
                {
                    "concept_id": concept["id"],
                    "concept_name": concept["name"],
                    "concept_type": concept["type"],
                    "episode_count": concept["episode_count"],
                    "episode_ids": concept["episode_ids"],
                    "speakers": concept.get("speakers", []),
                    "avg_confidence": concept.get("avg_confidence", 1.0),
                }
            )

        self.logger.info(
            "recurring_themes_found",
            extra={"context": {"count": len(themes)}},
        )

        return themes

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cross-episode statistics.

        Returns:
            Dictionary with statistics
        """
        # Count concepts in multiple episodes
        multi_episode_concepts = self.find_cross_episode_concepts(min_episodes=2)
        
        # Count relationships across episodes
        multi_episode_rels = self.find_cross_episode_relationships(min_episodes=2)
        
        # Count CROSS_EPISODE relationships
        query = f"""
        MATCH (a)-[r:{RelationshipTypes.CROSS_EPISODE}]->(b)
        WHERE a.workspace_id = $workspace_id
          AND b.workspace_id = $workspace_id
        RETURN count(r) as count
        """
        result = self.client.execute_read(
            query, {"workspace_id": self.workspace_id}
        )
        cross_episode_count = result[0]["count"] if result else 0

        # Count total unique episodes
        query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND c.episode_ids IS NOT NULL
        WITH c.episode_ids as episodes
        UNWIND episodes as ep
        RETURN count(DISTINCT ep) as unique_episodes
        """
        result = self.client.execute_read(
            query, {"workspace_id": self.workspace_id}
        )
        unique_episodes = result[0]["unique_episodes"] if result else 0

        return {
            "concepts_in_multiple_episodes": len(multi_episode_concepts),
            "relationships_across_episodes": len(multi_episode_rels),
            "cross_episode_relationships": cross_episode_count,
            "unique_episodes": unique_episodes,
            "top_concepts_by_episode_count": [
                {
                    "name": c["name"],
                    "type": c["type"],
                    "episode_count": c["episode_count"],
                }
                for c in multi_episode_concepts[:10]
            ],
        }


def find_cross_episode_concepts(
    client: Neo4jClient,
    min_episodes: int = 2,
    workspace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find concepts appearing in multiple episodes (convenience function).

    Args:
        client: Neo4j client
        min_episodes: Minimum episodes required
        workspace_id: Workspace identifier

    Returns:
        List of concept dictionaries
    """
    linker = CrossEpisodeLinker(client, workspace_id=workspace_id)
    return linker.find_cross_episode_concepts(min_episodes=min_episodes)


def find_cross_episode_relationships(
    client: Neo4jClient,
    min_episodes: int = 2,
    workspace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find relationships appearing across episodes (convenience function).

    Args:
        client: Neo4j client
        min_episodes: Minimum episodes required
        workspace_id: Workspace identifier

    Returns:
        List of relationship dictionaries
    """
    linker = CrossEpisodeLinker(client, workspace_id=workspace_id)
    return linker.find_cross_episode_relationships(min_episodes=min_episodes)


def create_cross_episode_links(
    client: Neo4jClient,
    min_episodes: int = 2,
    min_co_occurrences: int = 2,
    min_confidence: float = 0.5,
    workspace_id: Optional[str] = None,
) -> Dict[str, int]:
    """
    Create CROSS_EPISODE relationships (convenience function).

    Args:
        client: Neo4j client
        min_episodes: Minimum episodes each concept must appear in
        min_co_occurrences: Minimum co-occurrences required
        min_confidence: Minimum confidence threshold
        workspace_id: Workspace identifier

    Returns:
        Dictionary with creation statistics
    """
    linker = CrossEpisodeLinker(client, workspace_id=workspace_id)
    return linker.create_cross_episode_links(
        min_episodes=min_episodes,
        min_co_occurrences=min_co_occurrences,
        min_confidence=min_confidence,
    )

