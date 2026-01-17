#!/usr/bin/env python3
"""
Enhanced ingestion script with comprehensive cost and performance tracking (ASYNC version).
Intelligently skips steps that are already complete.

Usage:
    python process_with_metrics_async.py [--workspace WORKSPACE_ID] [--output-dir OUTPUT_DIR]
                                        [--max-concurrent MAX_CONCURRENT] [--batch-size BATCH_SIZE]
                                        [--force] [--skip-kg] [--skip-embeddings]
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import time
import asyncio

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.ingestion.loader import load_transcripts
from core_engine.chunking import chunk_documents
from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.kg.schema import initialize_schema
from core_engine.kg.pipeline_async import extract_kg_from_chunks_async
from core_engine.embeddings.ingest_qdrant_async import ingest_qdrant_async
from core_engine.metrics import (
    get_cost_tracker,
    get_performance_tracker,
    reset_cost_tracker,
    reset_performance_tracker,
)
from core_engine.metrics.reporting import (
    print_combined_report,
    save_reports,
)
from core_engine.metrics.langsmith_integration import (
    is_langsmith_enabled,
    langsmith_run,
)
from contextlib import nullcontext
from core_engine.logging import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


def check_kg_exists(workspace_id: str) -> dict:
    """Check if KG data already exists for workspace."""
    client = get_neo4j_client(workspace_id=workspace_id)
    try:
        # Check concepts
        concepts_query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (c:Concept OR c:Practice OR c:CognitiveState OR c:BehavioralPattern 
               OR c:Principle OR c:Outcome OR c:Causality OR c:Person 
               OR c:Place OR c:Organization OR c:Event)
        RETURN count(c) as count
        """
        concepts_result = client.execute_read(concepts_query, {"workspace_id": workspace_id})
        concept_count = concepts_result[0]["count"] if concepts_result else 0
        
        # Check relationships
        rels_query = """
        MATCH (a)-[r]->(b)
        WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
        RETURN count(r) as count
        """
        rels_result = client.execute_read(rels_query, {"workspace_id": workspace_id})
        rel_count = rels_result[0]["count"] if rels_result else 0
        
        # Check quotes
        quotes_query = """
        MATCH (q:Quote)
        WHERE q.workspace_id = $workspace_id
        RETURN count(q) as count
        """
        quotes_result = client.execute_read(quotes_query, {"workspace_id": workspace_id})
        quote_count = quotes_result[0]["count"] if quotes_result else 0
        
        return {
            "exists": concept_count > 0 or rel_count > 0,
            "concepts": concept_count,
            "relationships": rel_count,
            "quotes": quote_count,
        }
    finally:
        client.close()


def check_embeddings_exist(workspace_id: str, collection_name: str) -> dict:
    """Check if embeddings already exist for workspace."""
    try:
        from qdrant_client import QdrantClient
        from core_engine.utils.env_helper import get_env
        
        qdrant_url = get_env("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = get_env("QDRANT_API_KEY")
        
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key if qdrant_api_key else None)
        
        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection_name not in collection_names:
            return {"exists": False, "count": 0}
        
        # Get collection info
        collection = client.get_collection(collection_name)
        point_count = collection.points_count
        
        return {
            "exists": point_count > 0,
            "count": point_count,
        }
    except Exception as e:
        logger.warning(f"Could not check embeddings: {e}")
        return {"exists": False, "count": 0}


# Custom logger to tee output to file and console
class TeeLogger:
    def __init__(self, filepath, mode='a'):
        self.filepath = filepath
        self.mode = mode
        self.file = None
        self.console = sys.stdout

    def write(self, message):
        self.console.write(message)
        if self.file:
            self.file.write(message)

    def flush(self):
        self.console.flush()
        if self.file:
            self.file.flush()

    def open(self):
        self.file = open(self.filepath, self.mode)

    def close(self):
        if self.file:
            self.file.close()
            self.file = None

    def __enter__(self):
        self.open()
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.console
        self.close()


async def process_with_metrics_async(
    transcripts_dir: Path,
    workspace_id: str = "default",
    output_dir: Optional[Path] = None,
    clear_existing: bool = False,
    log_file: Optional[Path] = None,
    max_concurrent: int = 20,
    batch_size: int = 10,
    force: bool = False,
    skip_kg: bool = False,
    skip_embeddings: bool = False,
) -> dict:
    """
    Process transcripts with full cost and performance tracking asynchronously.
    Intelligently skips steps that are already complete.
    """
    metrics_dir = output_dir or (ROOT / "metrics" / workspace_id)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    log_path = log_file or (metrics_dir / "all_files_processings.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    cost_tracker = get_cost_tracker(save_path=metrics_dir / "cost_data.json")
    perf_tracker = get_performance_tracker(save_path=metrics_dir / "performance_data.json")
    
    reset_cost_tracker()
    reset_performance_tracker()
    
    with TeeLogger(log_path) as tee:
        print(f"\n{'=' * 80}")
        print("🚀 STARTING ASYNC INGESTION WITH PARALLEL PROCESSING")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Workspace: {workspace_id}")
        print(f"Transcripts: {transcripts_dir}")
        print(f"Metrics Output: {metrics_dir}")
        print(f"Log File: {log_path}")
        print(f"Max Concurrent: {max_concurrent} API calls")
        print(f"Batch Size: {batch_size} chunks per batch")
        print(f"Force Re-run: {force}")
        print(f"Skip KG: {skip_kg}")
        print(f"Skip Embeddings: {skip_embeddings}")
        if is_langsmith_enabled():
            print(f"✅ LangSmith: Enabled (view traces at https://smith.langchain.com)")
        else:
            print(f"ℹ️  LangSmith: Not enabled (see LANGSMITH_SETUP.md)")
        print("=" * 80 + "\n")
        
        results = {}
        
        run_context = langsmith_run(
            "full_ingestion_async",
            inputs={
                "workspace_id": workspace_id,
                "transcripts_dir": str(transcripts_dir),
                "max_concurrent": max_concurrent,
                "batch_size": batch_size,
            },
            metadata={
                "workspace": workspace_id,
                "output_dir": str(metrics_dir),
                "async": True,
            },
            tags=["ingestion", "pipeline", "async", workspace_id]
        ) if is_langsmith_enabled() else nullcontext()
        
        try:
            with run_context:
                # Step 1: Load transcripts
                print("📁 Step 1: Loading transcripts...")
                op_id = perf_tracker.start_operation("load_transcripts")
                docs = load_transcripts(transcripts_dir, workspace_id=workspace_id)
                perf_tracker.finish_operation(op_id, items_processed=len(docs))
                
                if not docs:
                    raise ValueError(f"No transcripts found in {transcripts_dir}")
                
                print(f"✅ Loaded {len(docs)} transcript file(s)")
                file_names = [Path(d.metadata['source_path']).name for d in docs]
                print(f"   Files: {', '.join(file_names[:5])}{', ...' if len(file_names) > 5 else ''}")
                print(f"   ... and {len(file_names) - 5 if len(file_names) > 5 else 0} more file(s)\n")
                results["transcripts_loaded"] = len(docs)
                
                # Step 2: Chunk documents
                print("✂️  Step 2: Chunking documents...")
                op_id = perf_tracker.start_operation("chunk_documents")
                chunks = chunk_documents(docs, target_chars=2000, overlap_chars=200)
                perf_tracker.finish_operation(op_id, items_processed=len(chunks))
                
                print(f"✅ Created {len(chunks)} chunks from {len(docs)} transcript(s)")
                print(f"   Average: {len(chunks) // len(docs) if len(docs) > 0 else 0} chunks per transcript\n")
                results["chunks_created"] = len(chunks)
                
                # Step 3: Initialize Neo4j schema
                print("🔧 Step 3: Initializing Neo4j schema...")
                op_id = perf_tracker.start_operation("initialize_schema")
                client = get_neo4j_client(workspace_id=workspace_id)
                try:
                    initialize_schema(client)
                    perf_tracker.finish_operation(op_id)
                    print("✅ Schema initialized\n")
                except Exception as e:
                    perf_tracker.finish_operation(op_id, metadata={"error": str(e)})
                    print(f"⚠️  Schema warning: {e}\n")
                finally:
                    client.close()
                
                # Step 4: Extract KG (ASYNC - PARALLEL PROCESSING)
                # Check if KG already exists (for informational purposes)
                kg_status = check_kg_exists(workspace_id)
                
                if skip_kg:
                    print("⏭️  Step 4: SKIPPING KG extraction (--skip-kg flag)\n")
                    results["kg_extraction"] = {
                        "concepts": kg_status["concepts"],
                        "relationships": kg_status["relationships"],
                        "quotes": kg_status["quotes"],
                        "skipped": True,
                    }
                else:
                    # Incremental processing: Always process KG (MERGE handles deduplication)
                    # This allows adding KG from new files while safely merging with existing
                    if kg_status["exists"]:
                        print(f"📊 Step 4: Extracting KG (incremental mode)")
                        print(f"   Existing: {kg_status['concepts']} concepts, {kg_status['relationships']} relationships, {kg_status['quotes']} quotes")
                        print(f"   Processing {len(docs)} file(s) - new content will be added to existing KG")
                        print(f"   Note: MERGE operations will prevent duplicates automatically\n")
                    else:
                        print("🧠 Step 4: Extracting knowledge graph (initial creation)...")
                    
                    total_batches = (len(chunks) + batch_size - 1) // batch_size
                    if not kg_status["exists"]:
                        print(f"   Total chunks: {len(chunks)}")
                        print(f"   Total batches: {total_batches}")
                        print(f"   Batch size: {batch_size} chunks per API call")
                        print(f"   Max concurrent: {max_concurrent} parallel API calls")
                        print(f"   Estimated time: {total_batches * 20 / max_concurrent / 60:.1f}-{total_batches * 30 / max_concurrent / 60:.1f} minutes\n")
                    print("=" * 80)
                    print("📊 PROGRESS:")
                    print("=" * 80)
                    
                    op_id = perf_tracker.start_operation("extract_kg_async")
                    
                    # Extract KG using async parallel processing
                    kg_results = await extract_kg_from_chunks_async(
                        chunks=chunks,
                        workspace_id=workspace_id,
                        model="gpt-4o",
                        batch_size=batch_size,
                        max_concurrent=max_concurrent,
                        confidence_threshold=0.5,
                        initialize_schema_first=False,
                    )
                    
                    perf_tracker.finish_operation(
                        op_id,
                        items_processed=len(chunks),
                        metadata={
                            "concepts": kg_results['written']['concepts'],
                            "relationships": kg_results['written']['relationships'],
                            "quotes": kg_results['written']['quotes'],
                            "max_concurrent": max_concurrent,
                            "batch_size": batch_size,
                        }
                    )
                    
                    print("\n" + "=" * 80)
                    print("✅ KG EXTRACTION COMPLETE")
                    print("=" * 80)
                    print(f"   Concepts: {kg_results['written']['concepts']}")
                    print(f"   Relationships: {kg_results['written']['relationships']}")
                    print(f"   Quotes: {kg_results['written']['quotes']}\n")
                    
                    results["kg_extraction"] = kg_results['written']
                
                # Step 5: Ingest to Qdrant (ASYNC - PARALLEL PROCESSING)
                collection_name = f"{workspace_id}_chunks"
                embeddings_status = check_embeddings_exist(workspace_id, collection_name)
                
                if skip_embeddings:
                    print("⏭️  Step 5: SKIPPING Embeddings (--skip-embeddings flag)\n")
                    results["embeddings_created"] = embeddings_status["count"]
                    results["embeddings_skipped"] = True
                elif embeddings_status["exists"] and not force:
                    print("⏭️  Step 5: SKIPPING Embeddings (already exist)")
                    print(f"   Existing: {embeddings_status['count']} embeddings")
                    print("   Use --force to re-run embeddings\n")
                    results["embeddings_created"] = embeddings_status["count"]
                    results["embeddings_skipped"] = True
                else:
                    print("📊 Step 5: Ingesting to Qdrant (ASYNC PARALLEL)...")
                    print(f"   Total chunks: {len(chunks)}")
                    print(f"   Creating embeddings with {max_concurrent} concurrent calls")
                    print(f"   Collection: {collection_name}\n")
                    print("=" * 80)
                    print("📊 EMBEDDING PROGRESS:")
                    print("=" * 80)
                    
                    op_id = perf_tracker.start_operation("ingest_qdrant_async")
                    await ingest_qdrant_async(
                        transcripts_path=transcripts_dir,
                        collection=collection_name,
                        workspace_id=workspace_id,
                        max_concurrent=max_concurrent,
                        batch_size=batch_size,
                    )
                    
                    perf_tracker.finish_operation(op_id, items_processed=len(chunks))
                    
                    print("\n✅ Vector embeddings stored in Qdrant\n")
                    results["embeddings_created"] = len(chunks)
                
                # Step 6: Generate reports
                print("📊 Step 6: Generating metrics reports...\n")
                print_combined_report()
                
                # Save reports
                save_reports(metrics_dir)
                
                results["metrics_saved"] = True
                
                print("\n" + "=" * 80)
                print("✅ INGESTION COMPLETE")
                print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 80)
                
                # LangSmith URL (if enabled and run context available)
                if is_langsmith_enabled() and run_context and hasattr(run_context, 'id'):
                    project = os.getenv("LANGCHAIN_PROJECT", "default")
                    print(f"\n🔍 View LangSmith traces at: https://smith.langchain.com/o/{os.getenv('LANGCHAIN_ORG_ID', 'default')}/projects/p/{project}/r/{run_context.id}")
                
                print(f"\n📄 Full log saved to: {log_path}")
            
            return results
                
        except Exception as e:
            logger.error("ingestion_failed", exc_info=True, extra={"error": str(e)})
            print(f"\n❌ ERROR: {e}\n")
            print(f"Error occurred at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Still generate reports for partial run
            print("\n📊 Generating partial metrics reports...\n")
            print_combined_report()
            save_reports(metrics_dir)
            
            print(f"\n📄 Full log (including error) saved to: {log_path}")
            
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process transcripts with cost and performance tracking (ASYNC) - Intelligently skips completed steps"
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default="default",
        help="Workspace ID (default: default)"
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        default=None,
        help="Directory containing transcripts (default: data/workspaces/{workspace}/transcripts)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save metrics reports (default: metrics/{workspace})"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing graph before processing (deprecated - use --force instead)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to save all console output to a file (default: metrics/{workspace}/all_files_processings.txt)"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=20,
        help="Maximum concurrent API calls for LLM and embeddings (default: 20)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of chunks to process per API call (default: 10)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run even if data already exists"
    )
    parser.add_argument(
        "--skip-kg",
        action="store_true",
        help="Skip KG extraction (only do embeddings)"
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embeddings (only do KG extraction)"
    )
    
    args = parser.parse_args()
    
    # Determine transcripts directory
    if args.transcripts_dir:
        transcripts_dir = Path(args.transcripts_dir)
    else:
        transcripts_dir = ROOT / "data" / "workspaces" / args.workspace / "transcripts"
    
    if not transcripts_dir.exists():
        print(f"❌ Transcripts directory not found: {transcripts_dir}")
        sys.exit(1)
    
    try:
        # Run the async processing function
        asyncio.run(
            process_with_metrics_async(
                transcripts_dir=transcripts_dir,
                workspace_id=args.workspace,
                output_dir=args.output_dir,
                clear_existing=args.clear,
                log_file=args.log_file,
                max_concurrent=args.max_concurrent,
                batch_size=args.batch_size,
                force=args.force,
                skip_kg=args.skip_kg,
                skip_embeddings=args.skip_embeddings,
            )
        )
        
        print("\n✅ Processing completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
