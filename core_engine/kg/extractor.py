"""
LLM-based knowledge extraction from chunks.
Uses GPT-4o with structured JSON output for deterministic extraction.
"""

from __future__ import annotations

import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("openai package not installed. Install with: pip install openai")

from langchain_core.documents import Document

from core_engine.logging import get_logger
from core_engine.kg.prompts import build_extraction_prompt
from core_engine.kg.schemas import EXTRACTION_SCHEMA, validate_extraction_output
from core_engine.utils.rate_limiter import RateLimiter, get_rate_limiter


def load_env() -> None:
    """Load environment variables."""
    try:
        load_dotenv()
    except Exception:
        pass


def get_openai_client() -> OpenAI:
    """Get OpenAI client."""
    load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


class KGExtractor:
    """Extract knowledge (concepts, relationships, quotes) from chunks using LLM."""

    def __init__(
        self,
        model: str = "gpt-4-turbo-preview",  # Default to accessible model
        temperature: float = 0.2,
        batch_size: int = 5,
        confidence_threshold: float = 0.5,
        workspace_id: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize KG extractor.

        Args:
            model: OpenAI model name
            temperature: LLM temperature (lower = more deterministic)
            batch_size: Number of chunks to process per LLM call
            confidence_threshold: Minimum confidence to include extraction
            workspace_id: Workspace identifier for logging
        """
        self.model = model
        self.temperature = temperature
        self.batch_size = batch_size
        self.confidence_threshold = confidence_threshold
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger("core_engine.kg.extractor", workspace_id=self.workspace_id)
        self.client = get_openai_client()
        
        # Rate limiter (default: 500 RPM, 1M TPM for GPT-4o)
        self.rate_limiter = rate_limiter or get_rate_limiter(
            requests_per_minute=500,
            tokens_per_minute=1_000_000,
        )

    def extract_from_chunks(
        self, chunks: List[Document]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract knowledge from chunks.

        Args:
            chunks: List of document chunks

        Returns:
            Dictionary with "concepts", "relationships", "quotes" arrays
        """
        all_concepts: List[Dict[str, Any]] = []
        all_relationships: List[Dict[str, Any]] = []
        all_quotes: List[Dict[str, Any]] = []

        total_chunks = len(chunks)
        self.logger.info(
            "extraction_start",
            extra={
                "context": {
                    "total_chunks": total_chunks,
                    "batch_size": self.batch_size,
                }
            },
        )

        # Process chunks in batches
        for i in range(0, total_chunks, self.batch_size):
            batch = chunks[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size

            self.logger.info(
                "extraction_batch_start",
                extra={
                    "context": {
                        "batch": batch_num,
                        "total_batches": total_batches,
                        "chunks_in_batch": len(batch),
                    }
                },
            )

            try:
                result = self._extract_batch(batch)
                
                # Filter by confidence threshold
                concepts = [
                    c for c in result.get("concepts", [])
                    if c.get("confidence", 0) >= self.confidence_threshold
                ]
                relationships = [
                    r for r in result.get("relationships", [])
                    if r.get("confidence", 0) >= self.confidence_threshold
                ]
                quotes = [
                    q for q in result.get("quotes", [])
                    if q.get("confidence", 0) >= self.confidence_threshold
                ]

                all_concepts.extend(concepts)
                all_relationships.extend(relationships)
                all_quotes.extend(quotes)

                self.logger.info(
                    "extraction_batch_complete",
                    extra={
                        "context": {
                            "batch": batch_num,
                            "concepts": len(concepts),
                            "relationships": len(relationships),
                            "quotes": len(quotes),
                        }
                    },
                )

            except Exception as e:
                self.logger.error(
                    "extraction_batch_failed",
                    exc_info=True,
                    extra={
                        "context": {
                            "batch": batch_num,
                            "error": str(e),
                        }
                    },
                )
                # Continue with next batch
                continue

        self.logger.info(
            "extraction_complete",
            extra={
                "context": {
                    "total_concepts": len(all_concepts),
                    "total_relationships": len(all_relationships),
                    "total_quotes": len(all_quotes),
                }
            },
        )

        return {
            "concepts": all_concepts,
            "relationships": all_relationships,
            "quotes": all_quotes,
        }

    def _extract_batch(self, chunks: List[Document]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract knowledge from a batch of chunks.

        Args:
            chunks: List of document chunks

        Returns:
            Dictionary with extracted concepts, relationships, quotes
        """
        prompt = build_extraction_prompt(chunks)

        # Call OpenAI with structured output (with rate limiting and retry)
        def make_api_call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledge extraction expert. Extract structured knowledge from podcast transcripts. Return ONLY valid JSON, no explanatory text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},  # Force JSON output
            )
        
        # Use rate limiter with retry logic
        response = self.rate_limiter.retry_with_backoff(
            make_api_call,
            operation_name=f"KG extraction (batch of {len(chunks)} chunks)",
            on_retry=lambda attempt, error: self.logger.warning(
                f"Retry attempt {attempt} for KG extraction",
                extra={"error": str(error)}
            )
        )
        
        # Record token usage for rate limiting
        if response.usage:
            total_tokens = (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)
            self.rate_limiter._record_request(tokens=total_tokens)

        # Parse JSON response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            self.logger.error(
                "json_parse_error",
                extra={"context": {"error": str(e), "content_preview": content[:200]}},
            )
            raise ValueError(f"Invalid JSON response: {e}")

        # Validate output
        is_valid, error_msg = validate_extraction_output(data)
        if not is_valid:
            raise ValueError(f"Invalid extraction output: {error_msg}")

        # Enrich with chunk metadata
        enriched = self._enrich_with_metadata(data, chunks)

        return enriched

    def _enrich_with_metadata(
        self, data: Dict[str, Any], chunks: List[Document]
    ) -> Dict[str, Any]:
        """
        Enrich extracted data with chunk metadata.

        Args:
            data: Extracted data
            chunks: Source chunks

        Returns:
            Enriched data
        """
        # Get base metadata from first chunk (assuming all chunks from same episode)
        base_metadata = chunks[0].metadata if chunks else {}

        # Enrich concepts
        for concept in data.get("concepts", []):
            concept.setdefault("source_path", base_metadata.get("source_path"))
            concept.setdefault("episode_id", base_metadata.get("episode_id"))
            concept.setdefault("speaker", base_metadata.get("speaker"))
            concept.setdefault("timestamp", base_metadata.get("timestamp"))
            concept.setdefault("workspace_id", self.workspace_id)
            concept.setdefault("chunk_index", base_metadata.get("chunk_index"))

        # Enrich relationships
        for rel in data.get("relationships", []):
            rel.setdefault("source_path", base_metadata.get("source_path"))
            rel.setdefault("episode_id", base_metadata.get("episode_id"))
            rel.setdefault("speaker", base_metadata.get("speaker"))
            rel.setdefault("timestamp", base_metadata.get("timestamp"))
            rel.setdefault("workspace_id", self.workspace_id)
            rel.setdefault("chunk_index", base_metadata.get("chunk_index"))

        # Enrich quotes
        for quote in data.get("quotes", []):
            quote.setdefault("source_path", base_metadata.get("source_path"))
            quote.setdefault("episode_id", base_metadata.get("episode_id"))
            quote.setdefault("workspace_id", self.workspace_id)
            quote.setdefault("chunk_index", base_metadata.get("chunk_index"))
            # Use quote speaker if available, otherwise chunk speaker
            if not quote.get("speaker"):
                quote["speaker"] = base_metadata.get("speaker")
            if not quote.get("timestamp"):
                quote["timestamp"] = base_metadata.get("timestamp")

        return data


def extract_from_chunks(
    chunks: List[Document],
    model: str = "gpt-4o",
    batch_size: int = 5,
    confidence_threshold: float = 0.5,
    workspace_id: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract knowledge from chunks (convenience function).

    Args:
        chunks: List of document chunks
        model: OpenAI model name
        batch_size: Number of chunks per LLM call
        confidence_threshold: Minimum confidence score
        workspace_id: Workspace identifier

    Returns:
        Dictionary with "concepts", "relationships", "quotes"
    """
    extractor = KGExtractor(
        model=model,
        batch_size=batch_size,
        confidence_threshold=confidence_threshold,
        workspace_id=workspace_id,
    )
    return extractor.extract_from_chunks(chunks)

