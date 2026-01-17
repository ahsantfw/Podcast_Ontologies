"""
Ingestion Service - Background processing
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.ingestion.loader import load_transcripts
from core_engine.chunking import chunk_documents
from core_engine.kg import extract_kg_from_chunks, get_neo4j_client, initialize_schema, CrossEpisodeLinker
from core_engine.embeddings.ingest_qdrant import ingest_qdrant
from core_engine.logging import get_logger
from backend.app.database.job_db import JobDB

logger = get_logger(__name__)

def process_transcripts_background(
    job_id: str,
    workspace_id: str,
    upload_id: str,
    clear_existing: bool = False
):
    """
    Background task to process transcripts.
    Updates job status in database as it progresses.
    """
    job_db = JobDB()
    
    try:
        # Update status: processing
        job_db.update_job(job_id, status="processing", progress=0)
        
        # Load transcripts from workspace directory
        transcripts_dir = ROOT / "data" / "workspaces" / workspace_id / "transcripts"
        
        if not transcripts_dir.exists():
            raise ValueError(f"Transcripts directory not found: {transcripts_dir}")
        
        logger.info("background_processing_started", extra={
            "job_id": job_id,
            "workspace_id": workspace_id,
            "transcripts_dir": str(transcripts_dir)
        })
        
        # Step 1: Load transcripts (10%)
        job_db.update_job(job_id, progress=10)
        docs = load_transcripts(transcripts_dir, workspace_id=workspace_id)
        
        if not docs:
            raise ValueError("No transcripts found")
        
        # Step 2: Chunk documents (20%)
        job_db.update_job(job_id, progress=20)
        chunks = chunk_documents(docs, target_chars=2000, overlap_chars=200)
        
        total_chunks = len(chunks)
        logger.info("chunking_complete", extra={"total_chunks": total_chunks})
        
        # Step 3: Initialize schema (25%)
        job_db.update_job(job_id, progress=25)
        client = get_neo4j_client(workspace_id=workspace_id)
        try:
            initialize_schema(client)
        finally:
            client.close()
        
        # Step 4: Extract KG (25% → 75%)
        # Process in batches and update progress
        batch_size = 10
        processed = 0
        
        job_db.update_job(job_id, progress=30)
        
        results = extract_kg_from_chunks(
            chunks=chunks,
            workspace_id=workspace_id,
            model="gpt-4o",
            batch_size=batch_size,
            confidence_threshold=0.5,
            initialize_schema_first=False,
        )
        
        # Update progress based on chunks processed
        processed = total_chunks
        progress = 30 + int((processed / total_chunks) * 45)  # 30% → 75%
        job_db.update_job(job_id, progress=progress)
        
        logger.info("kg_extraction_complete", extra={
            "concepts": results['written']['concepts'],
            "relationships": results['written']['relationships']
        })
        
        # Step 5: Ingest to Qdrant (75% → 85%)
        job_db.update_job(job_id, progress=75)
        
        collection_name = f"{workspace_id}_chunks"
        ingest_qdrant(
            transcripts_path=transcripts_dir,
            collection=collection_name,
            workspace_id=workspace_id
        )
        
        job_db.update_job(job_id, progress=85)
        
        # Step 6: Cross-episode analysis (85% → 95%)
        job_db.update_job(job_id, progress=85)
        
        client = get_neo4j_client(workspace_id=workspace_id)
        try:
            linker = CrossEpisodeLinker(client, workspace_id=workspace_id)
            link_results = linker.create_cross_episode_links(
                min_episodes=2,
                min_co_occurrences=2,
                min_confidence=0.5
            )
        finally:
            client.close()
        
        job_db.update_job(job_id, progress=95)
        
        # Step 7: Complete (100%)
        job_db.update_job(
            job_id,
            status="completed",
            progress=100,
            results={
                "concepts": results['written']['concepts'],
                "relationships": results['written']['relationships'],
                "quotes": results['written']['quotes'],
                "cross_episode_links": link_results.get('created_links', 0),
                "total_files": len(docs),
                "total_chunks": total_chunks
            }
        )
        
        logger.info("background_processing_complete", extra={"job_id": job_id})
        
    except Exception as e:
        logger.error("background_processing_failed", exc_info=True, extra={
            "job_id": job_id,
            "error": str(e)
        })
        job_db.update_job(job_id, status="failed", error=str(e))

