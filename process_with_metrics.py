#!/usr/bin/env python3
"""
Enhanced ingestion script with comprehensive cost and performance tracking.

Usage:
    python process_with_metrics.py [--workspace WORKSPACE_ID] [--output-dir OUTPUT_DIR]
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.ingestion.loader import load_transcripts
from core_engine.chunking import chunk_documents
from core_engine.kg import extract_kg_from_chunks, get_neo4j_client, initialize_schema
from core_engine.embeddings.ingest_qdrant import ingest_qdrant
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
from core_engine.metrics.integration import patch_openai_client
from core_engine.metrics.langsmith_integration import (
    is_langsmith_enabled,
    langsmith_run,
    get_run_url,
)
from contextlib import nullcontext
from core_engine.logging import get_logger
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


class TeeLogger:
    """Log to both file and console."""
    def __init__(self, file_path: Path):
        self.file = open(file_path, 'w', encoding='utf-8')
        self.console = sys.stdout
        self.stderr = sys.stderr
        
    def write(self, message):
        """Write to both file and console."""
        self.file.write(message)
        self.file.flush()
        self.console.write(message)
        self.console.flush()
    
    def flush(self):
        """Flush both file and console."""
        self.file.flush()
        self.console.flush()
    
    def close(self):
        """Close the file."""
        self.file.close()
    
    def __enter__(self):
        """Context manager entry."""
        sys.stdout = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        sys.stdout = self.console
        self.close()


def process_with_metrics(
    transcripts_dir: Path,
    workspace_id: str = "default",
    output_dir: Optional[Path] = None,
    clear_existing: bool = False,
    log_file: Optional[Path] = None,
) -> dict:
    """
    Process transcripts with full cost and performance tracking.
    
    Args:
        transcripts_dir: Directory containing transcript files
        workspace_id: Workspace identifier
        output_dir: Optional directory to save metrics reports
        clear_existing: Whether to clear existing graph
        
    Returns:
        Dictionary with processing results and metrics
    """
    # Initialize trackers
    metrics_dir = output_dir or (ROOT / "metrics" / workspace_id)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging to file
    log_path = log_file or (metrics_dir / "all_files_processings.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    cost_tracker = get_cost_tracker(save_path=metrics_dir / "cost_data.json")
    perf_tracker = get_performance_tracker(save_path=metrics_dir / "performance_data.json")
    
    # Reset trackers for fresh run
    reset_cost_tracker()
    reset_performance_tracker()
    
    # Use TeeLogger to log to both file and console
    with TeeLogger(log_path) as tee:
        print(f"\n{'=' * 80}")
        print("🚀 STARTING ENHANCED INGESTION WITH METRICS TRACKING")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Workspace: {workspace_id}")
        print(f"Transcripts: {transcripts_dir}")
        print(f"Metrics Output: {metrics_dir}")
        print(f"Log File: {log_path}")
        if is_langsmith_enabled():
            print(f"✅ LangSmith: Enabled (view traces at https://smith.langchain.com)")
        else:
            print(f"ℹ️  LangSmith: Not enabled (see LANGSMITH_SETUP.md)")
        print("=" * 80 + "\n")
        
        results = {}
        
        # Wrap entire process in LangSmith run if enabled
        run_context = langsmith_run(
            "full_ingestion",
            inputs={
                "workspace_id": workspace_id,
                "transcripts_dir": str(transcripts_dir),
            },
            metadata={
                "workspace": workspace_id,
                "output_dir": str(metrics_dir),
            },
            tags=["ingestion", "pipeline", workspace_id]
        ) if is_langsmith_enabled() else None
        
        try:
            context = run_context if run_context else nullcontext()
            with context:
                # Step 1: Load transcripts
                print("📁 Step 1: Loading transcripts...")
                op_id = perf_tracker.start_operation("load_transcripts")
                docs = load_transcripts(transcripts_dir, workspace_id=workspace_id)
                perf_tracker.finish_operation(op_id, items_processed=len(docs))
                
                if not docs:
                    raise ValueError(f"No transcripts found in {transcripts_dir}")
                
                print(f"✅ Loaded {len(docs)} transcript(s)\n")
                results["transcripts_loaded"] = len(docs)
                
                # Step 2: Chunk documents
                print("✂️  Step 2: Chunking documents...")
                op_id = perf_tracker.start_operation("chunk_documents")
                chunks = chunk_documents(docs, target_chars=2000, overlap_chars=200)
                perf_tracker.finish_operation(op_id, items_processed=len(chunks))
                
                print(f"✅ Created {len(chunks)} chunks\n")
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
                
                # Step 4: Extract KG (with cost tracking)
                print("🧠 Step 4: Extracting knowledge graph...")
                print("   (This will track all LLM API calls and costs)\n")
                
                # Patch OpenAI client in extractor to track costs
                from core_engine.kg.extractor import get_openai_client
                original_get_client = get_openai_client
                def tracked_get_client():
                    client = original_get_client()
                    return patch_openai_client(client)
                
                # Monkey-patch the get_openai_client function
                import core_engine.kg.extractor as extractor_module
                extractor_module.get_openai_client = tracked_get_client
                
                op_id = perf_tracker.start_operation("extract_kg")
                
                # Extract KG (this will make LLM calls - now tracked!)
                kg_results = extract_kg_from_chunks(
                    chunks=chunks,
                    workspace_id=workspace_id,
                    model="gpt-4o",
                    batch_size=5,
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
                    }
                )
                
                print(f"✅ Extracted:")
                print(f"   - Concepts: {kg_results['written']['concepts']}")
                print(f"   - Relationships: {kg_results['written']['relationships']}")
                print(f"   - Quotes: {kg_results['written']['quotes']}\n")
                
                results["kg_extraction"] = kg_results['written']
                
                # Step 5: Ingest to Qdrant (with cost tracking)
                print("📊 Step 5: Ingesting to Qdrant for vector search...")
                print("   (This will track embedding API calls and costs)\n")
                
                # Patch OpenAI client in ingest_qdrant to track costs
                import core_engine.embeddings.ingest_qdrant as ingest_module
                
                # Create a tracked client wrapper
                original_embed_batch = ingest_module.embed_batch
                def tracked_embed_batch(client, model, texts):
                    # Patch the client before using it
                    tracked_client = patch_openai_client(client)
                    return original_embed_batch(tracked_client, model, texts)
                ingest_module.embed_batch = tracked_embed_batch
                
                op_id = perf_tracker.start_operation("ingest_qdrant")
                
                collection_name = f"{workspace_id}_chunks"
                ingest_qdrant(
                    transcripts_path=transcripts_dir,
                    collection=collection_name,
                    workspace_id=workspace_id
                )
                
                # Get chunk count for performance tracking
                # We'll estimate based on chunks created
                perf_tracker.finish_operation(op_id, items_processed=len(chunks))
                
                print("✅ Vector embeddings stored in Qdrant\n")
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
                
                if is_langsmith_enabled() and run_context:
                    print(f"\n🔍 View LangSmith traces at: https://smith.langchain.com")
                
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
        description="Process transcripts with cost and performance tracking"
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
        help="Clear existing graph before processing"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to log file (default: metrics/{workspace}/all_files_processings.txt)"
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
        results = process_with_metrics(
            transcripts_dir=transcripts_dir,
            workspace_id=args.workspace,
            output_dir=args.output_dir,
            clear_existing=args.clear,
            log_file=args.log_file,
        )
        
        print("\n✅ Processing completed successfully!")
        print(f"\nResults:")
        for key, value in results.items():
            print(f"  {key}: {value}")
        
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

