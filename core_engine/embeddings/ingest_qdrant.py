"""
Batch embeddings + Qdrant upsert for chunked documents.

Steps:
1) Load transcripts -> chunk -> embed.
2) Upsert vectors + rich metadata to Qdrant.

Environment (.env at repo root):
  OPENAI_API_KEY=
  QDRANT_URL=http://localhost:6333
  QDRANT_API_KEY=   # optional for local
  QDRANT_COLLECTION=ontology_chunks
  EMBED_MODEL=text-embedding-3-large
  EMBED_DIM=3072
  WORKSPACE_ID=default
"""

from __future__ import annotations

import os
import hashlib
from pathlib import Path
import sys
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient, models

# Ensure repo root on sys.path when run as a script
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.ingestion.loader import load_transcripts
from core_engine.chunking import chunk_documents


def load_env() -> None:
    # Load .env if present; ignore errors if absent.
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


MAX_CHARS_PER_EMBED = 4000  # ~1k tokens - optimal for embedding throughput
MIN_CHARS_PER_CHUNK = 400  # Minimum chunk size to embed


def trim_text(text: str, max_chars: int = MAX_CHARS_PER_EMBED) -> str:
    """Trim text to max chars for embedding API."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def embed_batch(client: OpenAI, model: str, texts: List[str], rate_limiter=None) -> List[List[float]]:
    """Embed batch with rate limiting and retry."""
    from core_engine.utils.rate_limiter import get_rate_limiter
    
    safe_inputs = [trim_text(t) for t in texts]
    
    # Use rate limiter if provided, otherwise create default
    if rate_limiter is None:
        rate_limiter = get_rate_limiter(
            requests_per_minute=500,  # Embeddings have higher limits
            tokens_per_minute=5_000_000,  # Higher for embeddings
        )
    
    def make_embedding_call():
        return client.embeddings.create(model=model, input=safe_inputs)
    
    # Use rate limiter with retry logic
    resp = rate_limiter.retry_with_backoff(
        make_embedding_call,
        operation_name=f"Embeddings (batch of {len(texts)} texts)",
    )
    
    # Record token usage
    if resp.usage:
        rate_limiter._record_request(tokens=resp.usage.total_tokens or 0)
    
    return [d.embedding for d in resp.data]


def to_points(chunks, vectors: List[List[float]]) -> List[models.PointStruct]:
    """Convert chunks to Qdrant points with deterministic IDs to prevent duplicates."""
    points: List[models.PointStruct] = []
    for ch, vec in zip(chunks, vectors):
        meta = ch.metadata
        episode_id = meta.get("episode_id", "unknown")
        source_path = meta.get("source_path", "")
        chunk_index = meta.get("chunk_index", 0)
        start_char = meta.get("start_char", 0)
        
        # Create deterministic ID based on content + metadata
        # This ensures same chunk = same ID (no duplicates on reprocessing)
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
                id=point_id,  # Deterministic ID - prevents duplicates
                vector=vec,
                payload=payload,
            )
        )
    return points


def ingest_qdrant(
    transcripts_path: Path,
    collection: str,
    embed_model: str = "text-embedding-3-large",
    embed_dim: int = 3072,
    batch_size: int = 50,
    target_chars: int = 2000,  # Increased to reduce chunk count
    overlap_chars: int = 200,  # Increased proportionally
    workspace_id: Optional[str] = None,
) -> None:
    import time
    
    load_env()
    openai_api_key = get_env("OPENAI_API_KEY")
    qdrant_url = get_env("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = get_env("QDRANT_API_KEY")
    qdrant_timeout = int(get_env("QDRANT_TIMEOUT", 60))

    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    client = OpenAI(api_key=openai_api_key)
    qdrant = get_qdrant_client(qdrant_url, qdrant_api_key, timeout=qdrant_timeout)
    ensure_collection(qdrant, collection, vector_size=embed_dim)

    docs = load_transcripts(transcripts_path, workspace_id=workspace_id)
    chunks = chunk_documents(
        docs,
        target_chars=target_chars,
        overlap_chars=overlap_chars,
    )

    # Filter chunks: remove tiny and oversized chunks before embedding
    filtered_chunks = [
        c for c in chunks
        if MIN_CHARS_PER_CHUNK <= len(c.page_content) <= MAX_CHARS_PER_EMBED
    ]
    
    filtered_count = len(chunks) - len(filtered_chunks)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} chunks (outside {MIN_CHARS_PER_CHUNK}-{MAX_CHARS_PER_EMBED} char range)")

    # Embed and upsert in batches
    total = len(filtered_chunks)
    start_time = time.time()
    print(f"Processing {total} chunks in batches of {batch_size}...")
    
    # Create rate limiter for embeddings
    from core_engine.utils.rate_limiter import get_rate_limiter
    embed_rate_limiter = get_rate_limiter(
        requests_per_minute=500,
        tokens_per_minute=5_000_000,  # Higher for embeddings
    )
    
    for i in range(0, total, batch_size):
        batch_start = time.time()
        batch = filtered_chunks[i : i + batch_size]
        vectors = embed_batch(client, embed_model, [c.page_content for c in batch], rate_limiter=embed_rate_limiter)
        points = to_points(batch, vectors)
        # Use wait=False for non-blocking async writes
        qdrant.upsert(collection_name=collection, points=points, wait=False)
        batch_time = time.time() - batch_start
        processed = min(i+batch_size, total)
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / rate if rate > 0 else 0
        print(f"Upserted {processed}/{total} ({processed*100//total}%) | Batch: {batch_time:.1f}s | Rate: {rate:.1f} chunks/s | ETA: {eta/60:.1f} min")

    print(f"Ingested {len(filtered_chunks)} chunks into Qdrant collection '{collection}'.")


def main():
    load_env()
    transcripts_root = Path(get_env("TRANSCRIPTS_PATH", "data/transcripts"))
    collection = get_env("QDRANT_COLLECTION", "ontology_chunks")
    embed_model = get_env("EMBED_MODEL", "text-embedding-3-large")
    embed_dim = int(get_env("EMBED_DIM", 3072))
    workspace = get_env("WORKSPACE_ID", "default")
    batch_size = int(get_env("EMBED_BATCH_SIZE", 50))
    target_chars = int(get_env("CHUNK_TARGET_CHARS", 2000))  # Increased default
    overlap_chars = int(get_env("CHUNK_OVERLAP_CHARS", 200))  # Increased default

    ingest_qdrant(
        transcripts_path=transcripts_root,
        collection=collection,
        embed_model=embed_model,
        embed_dim=embed_dim,
        batch_size=batch_size,
        target_chars=target_chars,
        overlap_chars=overlap_chars,
        workspace_id=workspace,
    )


if __name__ == "__main__":
    main()

