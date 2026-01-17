"""
Neo4j schema definitions for knowledge graph.
Defines node labels, relationship types, properties, indexes, and constraints.
"""

from __future__ import annotations

from typing import List, Dict, Any
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger


# Node Labels
class NodeLabels:
    """Node label constants."""
    CONCEPT = "Concept"
    PERSON = "Person"
    PLACE = "Place"
    ORGANIZATION = "Organization"
    EVENT = "Event"
    QUOTE = "Quote"
    EPISODE = "Episode"
    PRACTICE = "Practice"
    COGNITIVE_STATE = "CognitiveState"
    BEHAVIORAL_PATTERN = "BehavioralPattern"
    PRINCIPLE = "Principle"
    OUTCOME = "Outcome"
    CAUSALITY = "Causality"


# Relationship Types
class RelationshipTypes:
    """Relationship type constants."""
    CAUSES = "CAUSES"
    INFLUENCES = "INFLUENCES"
    OPTIMIZES = "OPTIMIZES"
    ENABLES = "ENABLES"
    REDUCES = "REDUCES"
    LEADS_TO = "LEADS_TO"
    REQUIRES = "REQUIRES"
    RELATES_TO = "RELATES_TO"
    IS_PART_OF = "IS_PART_OF"
    SAID = "SAID"
    ABOUT = "ABOUT"
    MENTIONED_IN = "MENTIONED_IN"
    CROSS_EPISODE = "CROSS_EPISODE"


class SchemaManager:
    """Manages Neo4j schema: indexes, constraints, and structure."""

    def __init__(self, client: Neo4jClient):
        """
        Initialize schema manager.

        Args:
            client: Neo4j client instance
        """
        self.client = client
        self.logger = get_logger(
            "core_engine.kg.schema",
            workspace_id=client.workspace_id,
        )

    def create_constraints(self) -> None:
        """Create unique constraints on nodes."""
        constraints = [
            # Concept constraints (using CREATE OR REPLACE for compatibility)
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT place_id IF NOT EXISTS FOR (p:Place) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT quote_id IF NOT EXISTS FOR (q:Quote) REQUIRE q.id IS UNIQUE",
            "CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT practice_id IF NOT EXISTS FOR (p:Practice) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT cognitive_state_id IF NOT EXISTS FOR (c:CognitiveState) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT behavioral_pattern_id IF NOT EXISTS FOR (b:BehavioralPattern) REQUIRE b.id IS UNIQUE",
            "CREATE CONSTRAINT principle_id IF NOT EXISTS FOR (p:Principle) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT outcome_id IF NOT EXISTS FOR (o:Outcome) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT causality_id IF NOT EXISTS FOR (c:Causality) REQUIRE c.id IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                self.client.execute_write(constraint)
                self.logger.info(
                    "constraint_created",
                    extra={"context": {"constraint": constraint}},
                )
            except Exception as e:
                # Constraint might already exist, that's okay
                if "already exists" not in str(e).lower():
                    self.logger.warning(
                        "constraint_creation_failed",
                        extra={"context": {"constraint": constraint, "error": str(e)}},
                    )

    def create_indexes(self) -> None:
        """Create indexes for performance."""
        indexes = [
            # Concept indexes
            "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX concept_type IF NOT EXISTS FOR (c:Concept) ON (c.type)",
            "CREATE INDEX concept_episode IF NOT EXISTS FOR (c:Concept) ON (c.episode_id)",
            "CREATE INDEX concept_workspace IF NOT EXISTS FOR (c:Concept) ON (c.workspace_id)",
            
            # Person indexes
            "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
            
            # Quote indexes
            "CREATE INDEX quote_speaker IF NOT EXISTS FOR (q:Quote) ON (q.speaker)",
            "CREATE INDEX quote_episode IF NOT EXISTS FOR (q:Quote) ON (q.episode_id)",
            "CREATE INDEX quote_timestamp IF NOT EXISTS FOR (q:Quote) ON (q.timestamp)",
            
            # Episode indexes
            "CREATE INDEX episode_id_idx IF NOT EXISTS FOR (e:Episode) ON (e.id)",
            
            # Relationship indexes (for faster traversal)
            "CREATE INDEX rel_source IF NOT EXISTS FOR ()-[r:CAUSES|INFLUENCES|OPTIMIZES|ENABLES|REDUCES|LEADS_TO|REQUIRES|RELATES_TO|IS_PART_OF]-() ON (r.source_path)",
            "CREATE INDEX rel_episode IF NOT EXISTS FOR ()-[r:CAUSES|INFLUENCES|OPTIMIZES|ENABLES|REDUCES|LEADS_TO|REQUIRES|RELATES_TO|IS_PART_OF]-() ON (r.episode_id)",
        ]

        for index in indexes:
            try:
                self.client.execute_write(index)
                self.logger.info(
                    "index_created",
                    extra={"context": {"index": index}},
                )
            except Exception as e:
                # Index might already exist, that's okay
                if "already exists" not in str(e).lower():
                    self.logger.warning(
                        "index_creation_failed",
                        extra={"context": {"index": index, "error": str(e)}},
                    )

    def initialize_schema(self) -> None:
        """Initialize complete schema: constraints and indexes."""
        self.logger.info("initializing_schema")
        self.create_constraints()
        self.create_indexes()
        self.logger.info("schema_initialization_complete")

    def clear_graph(self, workspace_id: Optional[str] = None) -> None:
        """
        Clear all nodes and relationships (use with caution!).

        Args:
            workspace_id: If provided, only clear nodes for this workspace
        """
        if workspace_id:
            query = """
            MATCH (n)
            WHERE n.workspace_id = $workspace_id
            DETACH DELETE n
            """
            self.client.execute_write(query, {"workspace_id": workspace_id})
            self.logger.warning(
                "graph_cleared_workspace",
                extra={"context": {"workspace_id": workspace_id}},
            )
        else:
            query = "MATCH (n) DETACH DELETE n"
            self.client.execute_write(query)
            self.logger.warning("graph_cleared_all")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        stats = {}

        # Node counts by label
        node_labels = [
            "Concept",
            "Person",
            "Place",
            "Organization",
            "Event",
            "Quote",
            "Episode",
            "Practice",
            "CognitiveState",
            "BehavioralPattern",
            "Principle",
            "Outcome",
            "Causality",
        ]

        for label in node_labels:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
            result = self.client.execute_read(query)
            stats[f"{label.lower()}_count"] = result[0]["count"] if result else 0

        # Relationship counts
        rel_types = [
            "CAUSES",
            "INFLUENCES",
            "OPTIMIZES",
            "ENABLES",
            "REDUCES",
            "LEADS_TO",
            "REQUIRES",
            "RELATES_TO",
            "IS_PART_OF",
        ]

        for rel_type in rel_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = self.client.execute_read(query)
            stats[f"{rel_type.lower()}_count"] = result[0]["count"] if result else 0

        # Total counts
        total_nodes = self.client.execute_read("MATCH (n) RETURN count(n) as count")
        total_rels = self.client.execute_read("MATCH ()-[r]->() RETURN count(r) as count")

        stats["total_nodes"] = total_nodes[0]["count"] if total_nodes else 0
        stats["total_relationships"] = total_rels[0]["count"] if total_rels else 0

        return stats


def initialize_schema(client: Neo4jClient) -> None:
    """
    Initialize Neo4j schema (constraints and indexes).

    Args:
        client: Neo4j client instance
    """
    manager = SchemaManager(client)
    manager.initialize_schema()

