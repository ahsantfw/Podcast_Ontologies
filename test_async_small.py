#!/usr/bin/env python3
"""
Quick test script to verify async implementation works.
Tests with a small batch of chunks.
"""

import sys
import asyncio
from pathlib import Path

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.ingestion.loader import load_transcripts
from core_engine.chunking import chunk_documents
from core_engine.kg.pipeline_async import extract_kg_from_chunks_async
from core_engine.logging import get_logger

logger = get_logger(__name__)


async def test_async_extraction():
    """Test async extraction with small batch."""
    print("=" * 80)
    print("🧪 TESTING ASYNC EXTRACTION")
    print("=" * 80)
    
    # Load a few transcripts
    transcripts_dir = ROOT / "data" / "transcripts"
    if not transcripts_dir.exists():
        print(f"❌ Transcripts directory not found: {transcripts_dir}")
        return
    
    print(f"📁 Loading transcripts from: {transcripts_dir}")
    docs = load_transcripts(transcripts_dir, workspace_id="default")
    
    if not docs:
        print("❌ No transcripts found")
        return
    
    print(f"✅ Loaded {len(docs)} transcript(s)")
    
    # Chunk documents
    print("✂️  Chunking documents...")
    chunks = chunk_documents(docs, target_chars=2000, overlap_chars=200)
    print(f"✅ Created {len(chunks)} chunks")
    
    # Test with first 50 chunks only
    test_chunks = chunks[:50]
    print(f"\n🧪 Testing with {len(test_chunks)} chunks (first 50)")
    print(f"   Max concurrent: 5 (test mode)")
    print(f"   Batch size: 5 chunks per batch\n")
    
    try:
        # Run async extraction
        import time
        start_time = time.time()
        
        results = await extract_kg_from_chunks_async(
            chunks=test_chunks,
            workspace_id="default",
            model="gpt-4o",
            batch_size=5,
            max_concurrent=5,  # Low for testing
            confidence_threshold=0.5,
            initialize_schema_first=True,
        )
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80)
        print(f"Time taken: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"\nResults:")
        print(f"  Concepts: {results['written']['concepts']}")
        print(f"  Relationships: {results['written']['relationships']}")
        print(f"  Quotes: {results['written']['quotes']}")
        print("\n✅ Async extraction is working!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(test_async_extraction())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

