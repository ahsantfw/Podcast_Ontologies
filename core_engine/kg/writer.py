"""
Neo4j writer for knowledge graph.
Handles batch writes of concepts, relationships, and quotes.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.kg.schema import NodeLabels, RelationshipTypes
from core_engine.logging import get_logger


class KGWriter:
    """Write extracted knowledge to Neo4j."""

    def __init__(self, client: Neo4jClient, workspace_id: Optional[str] = None):
        """
        Initialize KG writer.

        Args:
            client: Neo4j client
            workspace_id: Workspace identifier
        """
        self.client = client
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger("core_engine.kg.writer", workspace_id=self.workspace_id)

    def write_extraction(
        self, extraction: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, int]:
        """
        Write entire extraction to Neo4j.

        Args:
            extraction: Extraction result with concepts, relationships, quotes

        Returns:
            Dictionary with counts of written entities
        """
        concepts = extraction.get("concepts", [])
        relationships = extraction.get("relationships", [])
        quotes = extraction.get("quotes", [])

        self.logger.info(
            "write_extraction_start",
            extra={
                "context": {
                    "concepts": len(concepts),
                    "relationships": len(relationships),
                    "quotes": len(quotes),
                }
            },
        )

        # Write concepts
        concept_count = self.write_concepts(concepts)
        
        # Write relationships
        relationship_count = self.write_relationships(relationships)
        
        # Write quotes
        quote_count = self.write_quotes(quotes)

        self.logger.info(
            "write_extraction_complete",
            extra={
                "context": {
                    "concepts_written": concept_count,
                    "relationships_written": relationship_count,
                    "quotes_written": quote_count,
                }
            },
        )

        return {
            "concepts": concept_count,
            "relationships": relationship_count,
            "quotes": quote_count,
        }

    def write_concepts(self, concepts: List[Dict[str, Any]]) -> int:
        """
        Write concepts to Neo4j.

        Args:
            concepts: List of concept dictionaries

        Returns:
            Number of concepts written
        """
        if not concepts:
            return 0

        # Group by type for batch writes
        queries = []
        
        for concept in concepts:
            concept_type = concept.get("type", "Concept")
            label = self._get_node_label(concept_type)
            
            # Build properties
            # Note: Keep timestamp and speaker even if None for CASE statements
            props = {
                "id": concept.get("id"),
                "name": concept.get("name"),
                "type": concept_type,
                "description": concept.get("description", ""),
                "workspace_id": self.workspace_id,
                "source_path": concept.get("source_path") or "",
                "episode_id": concept.get("episode_id") or "",
                "speaker": concept.get("speaker"),  # Keep None for CASE
                "timestamp": concept.get("timestamp"),  # Keep None for CASE
                "start_char": concept.get("start_char") or 0,
                "end_char": concept.get("end_char") or 0,
                "text_span": concept.get("text_span", ""),
                "confidence": concept.get("confidence", 1.0),
            }
            
            # Remove None values except for timestamp and speaker (needed for CASE)
            props = {
                k: v for k, v in props.items() 
                if v is not None or k in ("timestamp", "speaker")
            }
            
            # Build MERGE query
            # MERGE on id only (unique constraint), then set workspace_id
            query = f"""
            MERGE (c:{label} {{id: $id}})
            ON CREATE SET
                c.workspace_id = $workspace_id,
                c.name = $name,
                c.type = $type,
                c.description = $description,
                c.source_paths = [$source_path],
                c.episode_ids = [$episode_id],
                c.speakers = CASE WHEN $speaker IS NOT NULL THEN [$speaker] ELSE [] END,
                c.timestamps = CASE WHEN $timestamp IS NOT NULL THEN [$timestamp] ELSE [] END,
                c.start_chars = [$start_char],
                c.end_chars = [$end_char],
                c.text_spans = [$text_span],
                c.confidences = [$confidence],
                c.created_at = datetime()
            ON MATCH SET
                c.workspace_id = COALESCE(c.workspace_id, $workspace_id),
                c.name = $name,
                c.description = COALESCE(c.description, $description),
                c.source_paths = CASE 
                    WHEN $source_path IN c.source_paths THEN c.source_paths 
                    ELSE c.source_paths + $source_path 
                END,
                c.episode_ids = CASE 
                    WHEN $episode_id IN c.episode_ids THEN c.episode_ids 
                    ELSE c.episode_ids + $episode_id 
                END,
                c.speakers = CASE 
                    WHEN $speaker IS NOT NULL AND NOT $speaker IN c.speakers 
                    THEN c.speakers + $speaker 
                    ELSE c.speakers 
                END,
                c.timestamps = CASE 
                    WHEN $timestamp IS NOT NULL AND NOT $timestamp IN c.timestamps 
                    THEN c.timestamps + $timestamp 
                    ELSE c.timestamps 
                END,
                c.start_chars = c.start_chars + $start_char,
                c.end_chars = c.end_chars + $end_char,
                c.text_spans = c.text_spans + $text_span,
                c.confidences = c.confidences + $confidence,
                c.updated_at = datetime()
            RETURN c.id as id
            """
            
            queries.append((query, props))

        # Execute in batches
        batch_size = 100
        written = 0
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            self.client.execute_write_batch(batch)
            written += len(batch)

        return written

    def write_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        """
        Write relationships to Neo4j.

        Args:
            relationships: List of relationship dictionaries

        Returns:
            Number of relationships written
        """
        if not relationships:
            return 0

        queries = []
        
        for rel in relationships:
            rel_type = rel.get("type", "RELATES_TO")
            source_id = rel.get("source_id")
            target_id = rel.get("target_id")
            
            if not source_id or not target_id:
                continue
            
            # Use label-agnostic MATCH (match by id and workspace_id regardless of label)
            # This works even if nodes have multiple labels
            
            props = {
                "source_id": source_id,
                "target_id": target_id,
                "workspace_id": self.workspace_id,
                "description": rel.get("description", ""),
                "source_path": rel.get("source_path") or "",
                "episode_id": rel.get("episode_id") or "",
                "speaker": rel.get("speaker"),  # Keep None for CASE
                "timestamp": rel.get("timestamp"),  # Keep None for CASE
                "start_char": rel.get("start_char") or 0,
                "end_char": rel.get("end_char") or 0,
                "text_span": rel.get("text_span", ""),
                "confidence": rel.get("confidence", 1.0),
            }
            
            # Keep timestamp and speaker even if None for CASE statements
            props = {
                k: v for k, v in props.items() 
                if v is not None or k in ("timestamp", "speaker")
            }
            
            # Use label-agnostic MATCH - match any node with the id and workspace_id
            # This works for Concept, Practice, Outcome, etc.
            query = f"""
            MATCH (source)
            WHERE source.id = $source_id AND source.workspace_id = $workspace_id
            MATCH (target)
            WHERE target.id = $target_id AND target.workspace_id = $workspace_id
            MERGE (source)-[r:{rel_type}]->(target)
            ON CREATE SET
                r.description = $description,
                r.source_paths = [$source_path],
                r.episode_ids = [$episode_id],
                r.speakers = CASE WHEN $speaker IS NOT NULL THEN [$speaker] ELSE [] END,
                r.timestamps = CASE WHEN $timestamp IS NOT NULL THEN [$timestamp] ELSE [] END,
                r.start_chars = [$start_char],
                r.end_chars = [$end_char],
                r.text_spans = [$text_span],
                r.confidences = [$confidence],
                r.created_at = datetime()
            ON MATCH SET
                r.description = COALESCE(r.description, $description),
                r.source_paths = CASE 
                    WHEN $source_path IN r.source_paths THEN r.source_paths 
                    ELSE r.source_paths + $source_path 
                END,
                r.episode_ids = CASE 
                    WHEN $episode_id IN r.episode_ids THEN r.episode_ids 
                    ELSE r.episode_ids + $episode_id 
                END,
                r.confidences = r.confidences + $confidence,
                r.updated_at = datetime()
            RETURN source.id as source_id, target.id as target_id, type(r) as rel_type
            """
            
            queries.append((query, props))

        # Execute in batches
        batch_size = 100
        written = 0
        failed = 0
        failed_details = []
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            try:
                results = self.client.execute_write_batch(batch)
                # Count successful writes (results that returned data)
                # A successful write returns at least one record with source_id, target_id, rel_type
                for j, result in enumerate(results):
                    if result and len(result) > 0:
                        written += 1
                    else:
                        # Query executed but returned no results - MATCH failed
                        failed += 1
                        query_idx = i + j
                        if query_idx < len(relationships):
                            rel = relationships[query_idx]
                            failed_details.append({
                                "source_id": rel.get("source_id"),
                                "target_id": rel.get("target_id"),
                                "type": rel.get("type"),
                            })
            except Exception as e:
                self.logger.error(
                    "relationship_batch_write_failed",
                    exc_info=True,
                    extra={
                        "context": {
                            "batch_start": i,
                            "batch_size": len(batch),
                            "error": str(e),
                        }
                    },
                )
                failed += len(batch)
        
        # Log details of failed relationships
        if failed_details:
            self.logger.warning(
                "relationship_write_failures",
                extra={
                    "context": {
                        "failed_count": len(failed_details),
                        "sample_failures": failed_details[:10],  # First 10 failures
                    }
                },
            )
        
        if failed > 0:
            self.logger.warning(
                "relationships_write_partial",
                extra={
                    "context": {
                        "written": written,
                        "failed": failed,
                        "total": len(queries),
                    }
                },
            )
        
        return written

    def write_quotes(self, quotes: List[Dict[str, Any]]) -> int:
        """
        Write quotes to Neo4j and link to concepts/speakers.

        Args:
            quotes: List of quote dictionaries

        Returns:
            Number of quotes written
        """
        if not quotes:
            return 0

        queries = []
        
        for quote in quotes:
            quote_id = f"quote_{quote.get('episode_id', 'unknown')}_{quote.get('start_char', 0)}"
            quote_text = quote.get("text", "")
            speaker = quote.get("speaker")
            related_concepts = quote.get("related_concepts", [])
            
            props = {
                "id": quote_id,
                "text": quote_text,
                "workspace_id": self.workspace_id,
                "speaker": speaker,  # Keep None if not available
                "timestamp": quote.get("timestamp"),  # Keep None if not available
                "source_path": quote.get("source_path") or "",
                "episode_id": quote.get("episode_id") or "",
                "start_char": quote.get("start_char") or 0,  # Default to 0
                "end_char": quote.get("end_char") or 0,  # Default to 0
                "confidence": quote.get("confidence", 1.0),
            }
            
            # Keep speaker and timestamp even if None (query handles them)
            props = {
                k: v for k, v in props.items() 
                if v is not None or k in ("speaker", "timestamp")
            }
            
            # Create quote node
            # MERGE on id only (unique constraint), then set workspace_id
            query = f"""
            MERGE (q:{NodeLabels.QUOTE} {{id: $id}})
            ON CREATE SET
                q.workspace_id = $workspace_id,
                q.text = $text,
                q.speaker = COALESCE($speaker, null),
                q.timestamp = COALESCE($timestamp, null),
                q.source_path = $source_path,
                q.episode_id = $episode_id,
                q.start_char = $start_char,
                q.end_char = $end_char,
                q.confidence = $confidence,
                q.created_at = datetime()
            ON MATCH SET
                q.workspace_id = COALESCE(q.workspace_id, $workspace_id),
                q.text = $text,
                q.updated_at = datetime()
            RETURN q.id as id
            """
            
            queries.append((query, props))
            
            # Link to concepts
            for concept_id in related_concepts:
                link_query = f"""
                MATCH (q:{NodeLabels.QUOTE} {{id: $quote_id, workspace_id: $workspace_id}})
                MATCH (c:Concept {{id: $concept_id, workspace_id: $workspace_id}})
                MERGE (q)-[:{RelationshipTypes.ABOUT}]->(c)
                """
                queries.append((link_query, {"quote_id": quote_id, "concept_id": concept_id, "workspace_id": self.workspace_id}))
            
            # Link to speaker (if Person node exists)
            if speaker:
                speaker_query = f"""
                MATCH (q:{NodeLabels.QUOTE} {{id: $quote_id, workspace_id: $workspace_id}})
                MATCH (p:{NodeLabels.PERSON} {{name: $speaker, workspace_id: $workspace_id}})
                MERGE (p)-[:{RelationshipTypes.SAID}]->(q)
                """
                queries.append((speaker_query, {"quote_id": quote_id, "speaker": speaker, "workspace_id": self.workspace_id}))

        # Execute in batches
        batch_size = 50  # Smaller batch for quotes (more complex)
        written = 0
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            self.client.execute_write_batch(batch)
            written += len(batch)

        return len(quotes)  # Return quote count, not query count

    def _get_node_label(self, concept_type: str) -> str:
        """Map concept type to Neo4j label."""
        label_map = {
            "Concept": NodeLabels.CONCEPT,
            "Practice": NodeLabels.PRACTICE,
            "CognitiveState": NodeLabels.COGNITIVE_STATE,
            "BehavioralPattern": NodeLabels.BEHAVIORAL_PATTERN,
            "Principle": NodeLabels.PRINCIPLE,
            "Outcome": NodeLabels.OUTCOME,
            "Causality": NodeLabels.CAUSALITY,
            "Person": NodeLabels.PERSON,
            "Place": NodeLabels.PLACE,
            "Organization": NodeLabels.ORGANIZATION,
            "Event": NodeLabels.EVENT,
        }
        return label_map.get(concept_type, NodeLabels.CONCEPT)


def write_extraction(
    extraction: Dict[str, List[Dict[str, Any]]],
    client: Neo4jClient,
    workspace_id: Optional[str] = None,
) -> Dict[str, int]:
    """
    Write extraction to Neo4j (convenience function).

    Args:
        extraction: Extraction result
        client: Neo4j client
        workspace_id: Workspace identifier

    Returns:
        Dictionary with counts of written entities
    """
    writer = KGWriter(client, workspace_id=workspace_id)
    return writer.write_extraction(extraction)

