"""
Async KG extraction pipeline with concurrent processing.
"""

from __future__ import annotations

from typing import List, Optional
from pathlib import Path
from langchain_core.documents import Document

from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.kg.schema import initialize_schema
from core_engine.kg.extractor_async import AsyncKGExtractor
from core_engine.kg.normalizer import EntityNormalizer
from core_engine.kg.writer import KGWriter
from core_engine.logging import get_logger
from core_engine.utils.rate_limiter import get_rate_limiter


class AsyncKGExtractionPipeline:
    """Async KG extraction pipeline with concurrent processing."""

    def __init__(
        self,
        workspace_id: Optional[str] = None,
        model: str = "gpt-4o",
        batch_size: int = 10,  # Increased default
        confidence_threshold: float = 0.5,
        max_concurrent: int = 20,  # Concurrent API calls
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ):
        """
        Initialize async KG extraction pipeline.

        Args:
            workspace_id: Workspace identifier
            model: OpenAI model name
            batch_size: Chunks per LLM call
            confidence_threshold: Minimum confidence score
            max_concurrent: Maximum concurrent API calls
            neo4j_uri: Neo4j URI (optional)
            neo4j_user: Neo4j username (optional)
            neo4j_password: Neo4j password (optional)
        """
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger("core_engine.kg.pipeline_async", workspace_id=self.workspace_id)
        
        # Initialize components
        self.client = get_neo4j_client(
            workspace_id=self.workspace_id,
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
        )
        
        # Shared rate limiter
        rate_limiter = get_rate_limiter(
            requests_per_minute=500,
            tokens_per_minute=1_000_000,
        )
        
        self.extractor = AsyncKGExtractor(
            model=model,
            batch_size=batch_size,
            confidence_threshold=confidence_threshold,
            workspace_id=self.workspace_id,
            max_concurrent=max_concurrent,
            rate_limiter=rate_limiter,
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

    async def process_chunks(self, chunks: List[Document]) -> dict:
        """
        Process chunks through the complete pipeline (async).

        Args:
            chunks: List of document chunks

        Returns:
            Dictionary with extraction statistics
        """
        self.logger.info(
            "async_pipeline_start",
            extra={"context": {"chunks": len(chunks)}},
        )

        # Step 1: Extract (async, concurrent)
        self.logger.info("step_extract_async")
        extraction = await self.extractor.extract_from_chunks(chunks)

        # Step 2: Normalize (sync, but fast)
        self.logger.info("step_normalize")
        normalized = self.normalizer.normalize_extraction(extraction)

        # Step 3: Write to Neo4j (sync, but fast)
        self.logger.info("step_write")
        counts = self.writer.write_extraction(normalized)

        self.logger.info(
            "async_pipeline_complete",
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


async def extract_kg_from_chunks_async(
    chunks: List[Document],
    workspace_id: Optional[str] = None,
    model: str = "gpt-4o",
    batch_size: int = 10,
    max_concurrent: int = 20,
    confidence_threshold: float = 0.5,
    initialize_schema_first: bool = True,
) -> dict:
    """
    Extract KG from chunks using async concurrent processing (convenience function).

    Args:
        chunks: List of document chunks
        workspace_id: Workspace identifier
        model: OpenAI model name
        batch_size: Chunks per LLM call
        max_concurrent: Maximum concurrent API calls
        confidence_threshold: Minimum confidence score
        initialize_schema_first: Whether to initialize schema before processing

    Returns:
        Dictionary with extraction statistics
    """
    pipeline = AsyncKGExtractionPipeline(
        workspace_id=workspace_id,
        model=model,
        batch_size=batch_size,
        max_concurrent=max_concurrent,
        confidence_threshold=confidence_threshold,
    )

    try:
        if initialize_schema_first:
            pipeline.initialize()
        
        return await pipeline.process_chunks(chunks)
    finally:
        pipeline.close()

