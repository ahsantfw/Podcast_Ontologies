"""
Knowledge Graph (KG) extraction module.

This module handles extraction of structured knowledge from chunks
and storage in Neo4j with full provenance tracking.
"""

from core_engine.kg.neo4j_client import Neo4jClient, get_neo4j_client
from core_engine.kg.schema import (
    SchemaManager,
    initialize_schema,
    NodeLabels,
    RelationshipTypes,
)
from core_engine.kg.extractor import KGExtractor, extract_from_chunks
from core_engine.kg.normalizer import EntityNormalizer, normalize_extraction
from core_engine.kg.writer import KGWriter, write_extraction
from core_engine.kg.pipeline import KGExtractionPipeline, extract_kg_from_chunks
from core_engine.kg.cross_episode import (
    CrossEpisodeLinker,
    find_cross_episode_concepts,
    find_cross_episode_relationships,
    create_cross_episode_links,
)

__all__ = [
    "Neo4jClient",
    "get_neo4j_client",
    "SchemaManager",
    "initialize_schema",
    "NodeLabels",
    "RelationshipTypes",
    "KGExtractor",
    "extract_from_chunks",
    "EntityNormalizer",
    "normalize_extraction",
    "KGWriter",
    "write_extraction",
    "KGExtractionPipeline",
    "extract_kg_from_chunks",
    "CrossEpisodeLinker",
    "find_cross_episode_concepts",
    "find_cross_episode_relationships",
    "create_cross_episode_links",
]

