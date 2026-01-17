"""
Async batch embeddings + Qdrant upsert with concurrent processing.
"""

from __future__ import annotations

import os
import hashlib
import asyncio
from pathlib import Path
import sys
from typing import List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from qdrant_client import QdrantClient, models

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.ingestion.loader import load_transcripts
from core_engine.chunking import chunk_documents
from core_engine.utils.rate_limiter import get_rate_limiter


def load_env() -> None:
    try:
        load_dotenv()
    except Exception:
        pass


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)


def get_qdrant_client(url: str, api_key: Optional[str], timeout: int) -> QdrantClient:
    return QdrantClient(url=url, api_key=api_key, timeout=timeout)


def ensure_collection(
    client: QdrantClient,
    collection: str,
    vector_size: int,
    distance: models.Distance = models.Distance.COSINE,
) -> None:
    exists = client.collection_exists(collection)
    if not exists:
        client.recreate_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=vector_size, distance=distance),
        )


MAX_CHARS_PER_EMBED = 4000
MIN_CHARS_PER_CHUNK = 400


def trim_text(text: str, max_chars: int = MAX_CHARS_PER_EMBED) -> str:
    """Trim text to max chars for embedding API."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


async def embed_batch_async(
    client: AsyncOpenAI,
    model: str,
    texts: List[str],
    rate_limiter=None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> List[List[float]]:
    """Embed batch with async processing and rate limiting."""
    from core_engine.utils.rate_limiter import get_rate_limiter
    
    safe_inputs = [trim_text(t) for t in texts]
    
    # Use semaphore if provided
    if semaphore:
        async with semaphore:
            return await _do_embed_batch(client, model, safe_inputs, rate_limiter)
    else:
        return await _do_embed_batch(client, model, safe_inputs, rate_limiter)


async def _do_embed_batch(
    client: AsyncOpenAI,
    model: str,
    inputs: List[str],
    rate_limiter,
) -> List[List[float]]:
    """Internal async embedding call with retry."""
    if rate_limiter is None:
        rate_limiter = get_rate_limiter(
            requests_per_minute=500,
            tokens_per_minute=5_000_000,
        )
    
    max_retries = 5
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Wait for rate limits (run blocking call in executor)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, rate_limiter._wait_for_rate_limit)
            
            # Make async API call
            resp = await client.embeddings.create(model=model, input=inputs)
            
            # Record token usage (thread-safe)
            if resp.usage:
                rate_limiter._record_request(tokens=resp.usage.total_tokens or 0)
            
            return [d.embedding for d in resp.data]
            
        except Exception as e:
            last_exception = e
            
            is_rate_limit = (
                hasattr(e, 'status_code') and e.status_code == 429
            ) or "rate limit" in str(e).lower()
            
            if attempt < max_retries:
                delay = max(60.0, 2.0 ** attempt) if is_rate_limit else min(2.0 ** attempt, 120.0)
                await asyncio.sleep(delay)
            else:
                raise
    
    if last_exception:
        raise last_exception
    raise RuntimeError("Failed to create embeddings")


def to_points(chunks, vectors: List[List[float]]) -> List[models.PointStruct]:
    """Convert chunks to Qdrant points with deterministic IDs."""
    points: List[models.PointStruct] = []
    for ch, vec in zip(chunks, vectors):
        meta = ch.metadata
        episode_id = meta.get("episode_id", "unknown")
        source_path = meta.get("source_path", "")
        chunk_index = meta.get("chunk_index", 0)
        start_char = meta.get("start_char", 0)
        
        id_string = f"{episode_id}:{source_path}:{chunk_index}:{start_char}:{ch.page_content[:100]}"
        point_id = hashlib.md5(id_string.encode()).hexdigest()
        
        payload = {
            "text": ch.page_content,
            "source_path": source_path,
            "episode_id": episode_id,
            "workspace_id": meta.get("workspace_id"),
            "chunk_index": chunk_index,
            "speaker": meta.get("speaker"),
            "speakers_in_chunk": meta.get("speakers_in_chunk"),
            "timestamp": meta.get("timestamp"),
            "timestamps_in_chunk": meta.get("timestamps_in_chunk"),
            "turns": meta.get("turns"),
            "start_char": start_char,
            "end_char": meta.get("end_char"),
        }
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vec,
                payload=payload,
            )
        )
    return points


async def ingest_qdrant_async(
    transcripts_path: Path,
    collection: str,
    embed_model: str = "text-embedding-3-large",
    embed_dim: int = 3072,
    batch_size: int = 50,
    max_concurrent: int = 20,
    target_chars: int = 2000,
    overlap_chars: int = 200,
    workspace_id: Optional[str] = None,
) -> None:
    """Async ingestion with concurrent embedding calls."""
    import time
    
    load_env()
    openai_api_key = get_env("OPENAI_API_KEY")
    qdrant_url = get_env("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = get_env("QDRANT_API_KEY")
    qdrant_timeout = int(get_env("QDRANT_TIMEOUT", 60))

    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    client = AsyncOpenAI(api_key=openai_api_key)
    qdrant = get_qdrant_client(qdrant_url, qdrant_api_key, timeout=qdrant_timeout)
    ensure_collection(qdrant, collection, vector_size=embed_dim)

    docs = load_transcripts(transcripts_path, workspace_id=workspace_id)
    chunks = chunk_documents(
        docs,
        target_chars=target_chars,
        overlap_chars=overlap_chars,
    )

    # Filter chunks
    filtered_chunks = [
        c for c in chunks
        if MIN_CHARS_PER_CHUNK <= len(c.page_content) <= MAX_CHARS_PER_EMBED
    ]
    
    filtered_count = len(chunks) - len(filtered_chunks)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} chunks (outside {MIN_CHARS_PER_CHUNK}-{MAX_CHARS_PER_EMBED} char range)")

    # Create rate limiter and semaphore
    rate_limiter = get_rate_limiter(
        requests_per_minute=500,
        tokens_per_minute=5_000_000,
    )
    semaphore = asyncio.Semaphore(max_concurrent)

    # Process in batches concurrently
    total = len(filtered_chunks)
    start_time = time.time()
    print(f"Processing {total} chunks in batches of {batch_size} with {max_concurrent} concurrent calls...")
    
    # Create batches
    batches = []
    for i in range(0, total, batch_size):
        batch = filtered_chunks[i : i + batch_size]
        batches.append((i, batch))
    
    # Progress tracking
    completed_batches = 0
    total_batches = len(batches)
    
    # Process batches concurrently with progress
    async def process_batch(batch_idx, batch):
        nonlocal completed_batches
        try:
            vectors = await embed_batch_async(
                client,
                embed_model,
                [c.page_content for c in batch],
                rate_limiter=rate_limiter,
                semaphore=semaphore,
            )
            points = to_points(batch, vectors)
            qdrant.upsert(collection_name=collection, points=points, wait=False)
            completed_batches += 1
            
            # Print progress
            elapsed = time.time() - start_time
            rate = (completed_batches * batch_size) / elapsed if elapsed > 0 else 0
            eta = (total - completed_batches * batch_size) / rate if rate > 0 else 0
            progress_pct = (completed_batches * 100) // total_batches
            
            print(f"✅ Embedded {completed_batches * batch_size}/{total} chunks ({progress_pct}%) | "
                  f"Rate: {rate:.1f} chunks/s | ETA: {eta/60:.1f} min", flush=True)
            
            return len(batch)
        except Exception as e:
            completed_batches += 1
            print(f"❌ Batch {completed_batches}/{total_batches} failed: {e}", flush=True)
            raise
    
    # Process all batches concurrently
    tasks = [process_batch(idx, batch) for idx, batch in batches]
    results = await asyncio.gather(*tasks)
    
    total_processed = sum(results)
    elapsed = time.time() - start_time
    rate = total_processed / elapsed if elapsed > 0 else 0
    
    print(f"\n✅ Ingested {total_processed} chunks into Qdrant collection '{collection}'.")
    print(f"   Total time: {elapsed/60:.1f} minutes")
    print(f"   Average rate: {rate:.1f} chunks/s")

