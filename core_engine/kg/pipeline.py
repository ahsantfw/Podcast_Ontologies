"""
Main KG extraction pipeline.
Orchestrates the complete extraction process: extract -> normalize -> write.
"""

from __future__ import annotations

from typing import List, Optional
from pathlib import Path
from langchain_core.documents import Document

from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.kg.schema import initialize_schema
from core_engine.kg.extractor import KGExtractor
from core_engine.kg.normalizer import EntityNormalizer
from core_engine.kg.writer import KGWriter
from core_engine.logging import get_logger


class KGExtractionPipeline:
    """Complete KG extraction pipeline."""

    def __init__(
        self,
        workspace_id: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",  # Default to accessible model
        batch_size: int = 5,
        confidence_threshold: float = 0.5,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ):
        """
        Initialize KG extraction pipeline.

        Args:
            workspace_id: Workspace identifier
            model: OpenAI model name
            batch_size: Chunks per LLM call
            confidence_threshold: Minimum confidence score
            neo4j_uri: Neo4j URI (optional, uses env if not provided)
            neo4j_user: Neo4j username (optional, uses env if not provided)
            neo4j_password: Neo4j password (optional, uses env if not provided)
        """
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger("core_engine.kg.pipeline", workspace_id=self.workspace_id)
        
        # Initialize components
        self.client = get_neo4j_client(
            workspace_id=self.workspace_id,
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
        )
        
        self.extractor = KGExtractor(
            model=model,
            batch_size=batch_size,
            confidence_threshold=confidence_threshold,
            workspace_id=self.workspace_id,
        )
        
        self.normalizer = EntityNormalizer(
            self.client,
            workspace_id=self.workspace_id,
        )
        
        self.writer = KGWriter(
            self.client,
            workspace_id=self.workspace_id,
        )

    def initialize(self) -> None:
        """Initialize Neo4j schema (constraints and indexes)."""
        self.logger.info("initializing_pipeline")
        initialize_schema(self.client)
        self.logger.info("pipeline_initialized")

    def process_chunks(self, chunks: List[Document]) -> dict:
        """
        Process chunks through the complete pipeline.

        Args:
            chunks: List of document chunks

        Returns:
            Dictionary with extraction statistics
        """
        self.logger.info(
            "pipeline_start",
            extra={"context": {"chunks": len(chunks)}},
        )

        # Step 1: Extract
        self.logger.info("step_extract")
        extraction = self.extractor.extract_from_chunks(chunks)

        # Step 2: Normalize
        self.logger.info("step_normalize")
        normalized = self.normalizer.normalize_extraction(extraction)

        # Step 3: Write to Neo4j
        self.logger.info("step_write")
        counts = self.writer.write_extraction(normalized)

        self.logger.info(
            "pipeline_complete",
            extra={
                "context": {
                    "concepts": counts.get("concepts", 0),
                    "relationships": counts.get("relationships", 0),
                    "quotes": counts.get("quotes", 0),
                }
            },
        )

        return {
            "extracted": {
                "concepts": len(extraction.get("concepts", [])),
                "relationships": len(extraction.get("relationships", [])),
                "quotes": len(extraction.get("quotes", [])),
            },
            "written": counts,
        }

    def close(self) -> None:
        """Close Neo4j connection."""
        self.client.close()


def extract_kg_from_chunks(
    chunks: List[Document],
    workspace_id: Optional[str] = None,
    model: str = "gpt-4-turbo-preview",  # Default to accessible model
    batch_size: int = 5,
    confidence_threshold: float = 0.5,
    initialize_schema_first: bool = True,
) -> dict:
    """
    Extract KG from chunks (convenience function).

    Args:
        chunks: List of document chunks
        workspace_id: Workspace identifier
        model: OpenAI model name
        batch_size: Chunks per LLM call
        confidence_threshold: Minimum confidence score
        initialize_schema_first: Whether to initialize schema before processing

    Returns:
        Dictionary with extraction statistics
    """
    pipeline = KGExtractionPipeline(
        workspace_id=workspace_id,
        model=model,
        batch_size=batch_size,
        confidence_threshold=confidence_threshold,
    )

    try:
        if initialize_schema_first:
            pipeline.initialize()
        
        return pipeline.process_chunks(chunks)
    finally:
        pipeline.close()

