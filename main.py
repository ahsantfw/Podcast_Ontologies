#!/usr/bin/env python3
"""
Single entry point for complete KG pipeline: Process transcripts + Query with RAG + KG hybrid.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

load_dotenv()

from core_engine.ingestion.loader import load_transcripts
from core_engine.chunking import chunk_documents
from core_engine.kg import extract_kg_from_chunks, get_neo4j_client, initialize_schema, CrossEpisodeLinker
from core_engine.embeddings.ingest_qdrant import ingest_qdrant
from core_engine.reasoning import create_reasoner
from core_engine.logging import get_logger


def get_env(key: str, default: str = None) -> str:
    """Get environment variable."""
    value = os.getenv(key, default)
    if value is None and default is None:
        raise RuntimeError(f"Environment variable {key} is required")
    return value


def process_transcripts(transcripts_dir: Path, workspace_id: str):
    """Process all transcript files."""
    print("🚀 Processing Transcripts to Knowledge Graph\n")
    
    # Load transcripts
    print("📁 Loading transcripts...")
    docs = load_transcripts(transcripts_dir, workspace_id=workspace_id)
    if not docs:
        print(f"❌ No transcripts found in {transcripts_dir}")
        return False
    
    print(f"✅ Loaded {len(docs)} transcript(s)\n")
    
    # Chunk documents
    print("✂️  Chunking documents...")
    chunks = chunk_documents(docs, target_chars=2000, overlap_chars=200)
    print(f"✅ Created {len(chunks)} chunks\n")
    
    # Initialize Neo4j schema
    print("🔧 Initializing Neo4j schema...")
    client = get_neo4j_client(workspace_id=workspace_id)
    try:
        initialize_schema(client)
        print("✅ Schema initialized\n")
    except Exception as e:
        print(f"⚠️  Schema warning: {e}\n")
    finally:
        client.close()
    
    # Extract KG
    print("🧠 Extracting knowledge graph...")
    results = extract_kg_from_chunks(
        chunks=chunks,
        workspace_id=workspace_id,
        model="gpt-4o",
        batch_size=5,
        confidence_threshold=0.5,
        initialize_schema_first=False,
    )
    
    print(f"✅ Extracted:")
    print(f"   - Concepts: {results['written']['concepts']}")
    print(f"   - Relationships: {results['written']['relationships']}")
    print(f"   - Quotes: {results['written']['quotes']}\n")
    
    # Ingest to Qdrant for RAG
    print("📊 Ingesting to Qdrant for vector search...")
    try:
        ingest_qdrant(
            transcripts_path=transcripts_dir,
            collection="ontology_chunks",
            workspace_id=workspace_id
        )
        print("✅ Vector embeddings stored in Qdrant\n")
    except Exception as e:
        print(f"⚠️  Qdrant ingestion warning: {e}")
        print("   (Vector search will not be available)\n")
    
    # Cross-episode analysis
    print("🔗 Running cross-episode analysis...")
    client = get_neo4j_client(workspace_id=workspace_id)
    try:
        linker = CrossEpisodeLinker(client, workspace_id=workspace_id)
        link_results = linker.create_cross_episode_links(
            min_episodes=2,
            min_co_occurrences=2,
            min_confidence=0.5
        )
        print(f"✅ Cross-episode links: {link_results['created_links']}\n")
    except Exception as e:
        print(f"⚠️  Cross-episode warning: {e}\n")
    finally:
        client.close()
    
    return True


def query_interactive(workspace_id: str, use_hybrid: bool = True):
    """Interactive query interface with hybrid RAG + KG."""
    print("=" * 60)
    print("🧠 Knowledge Graph Query Interface")
    if use_hybrid:
        print("🔀 Mode: Hybrid RAG + KG (Vector Search + Graph Query)")
    else:
        print("📊 Mode: Graph Only")
    print("=" * 60)
    print("Type 'exit' to quit")
    print("Type 'stats' to see graph statistics")
    print("=" * 60)
    print()
    
    reasoner = create_reasoner(
        workspace_id=workspace_id,
        use_llm=True,
        use_hybrid=use_hybrid,
    )
    
    session_id = None
    
    try:
        while True:
            question = input("💬 Question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ["exit", "quit"]:
                print("\n👋 Goodbye!")
                break
            
            if question.lower() == "stats":
                client = get_neo4j_client(workspace_id=workspace_id)
                try:
                    result = client.execute_read(
                        "MATCH (n) WHERE n.workspace_id = $workspace_id RETURN count(n) as total",
                        {"workspace_id": workspace_id}
                    )
                    total = result[0]["total"] if result else 0
                    result = client.execute_read(
                        "MATCH ()-[r]->() WHERE r.workspace_id = $workspace_id RETURN count(r) as total",
                        {"workspace_id": workspace_id}
                    )
                    rels = result[0]["total"] if result else 0
                    print(f"\n📊 Graph Statistics:")
                    print(f"   Total nodes: {total}")
                    print(f"   Total relationships: {rels}\n")
                finally:
                    client.close()
                continue
            
            # Query
            print("\n🔍 Querying...")
            try:
                result = reasoner.query(question, session_id=session_id)
                session_id = result["session_id"]
                
                print(f"\n💡 Answer:")
                print("-" * 60)
                print(result["answer"])
                print("-" * 60)
                
                # Display sources if available
                if result.get("sources"):
                    sources = result["sources"]
                    episode_ids = list(set([s.get("episode_id") for s in sources if s.get("episode_id")]))[:5]
                    if episode_ids:
                        print(f"\n📚 Sources: {', '.join(episode_ids)}")
                
                if result.get("metadata"):
                    meta = result["metadata"]
                    if meta.get("method"):
                        print(f"\n📝 Method: {meta['method']}")
                    if meta.get("rag_count"):
                        print(f"📄 RAG results: {meta['rag_count']}")
                    if meta.get("kg_count"):
                        print(f"🕸️  KG results: {meta['kg_count']}")
                    if meta.get("is_out_of_scope"):
                        print(f"⚠️  Note: This question may be outside the knowledge base scope")
                print()
                
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    finally:
        reasoner.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Complete KG Pipeline: Process transcripts and query with RAG + KG hybrid"
    )
    parser.add_argument(
        "command",
        choices=["process", "query", "all"],
        help="Command to run: process (transcripts), query (interactive), or all (process then query)"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("data/transcripts"),
        help="Input directory for transcripts (default: data/transcripts)"
    )
    parser.add_argument(
        "--workspace-id",
        default=None,
        help="Workspace identifier (default: from env or 'default')"
    )
    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Disable hybrid RAG + KG mode (use graph only)"
    )
    
    args = parser.parse_args()
    
    workspace_id = args.workspace_id or get_env("WORKSPACE_ID", "default")
    use_hybrid = not args.no_hybrid
    
    if args.command == "process":
        success = process_transcripts(args.input, workspace_id)
        if not success:
            sys.exit(1)
    
    elif args.command == "query":
        query_interactive(workspace_id, use_hybrid=use_hybrid)
    
    elif args.command == "all":
        # Process then query
        success = process_transcripts(args.input, workspace_id)
        if success:
            print("\n" + "=" * 60)
            print("✅ Processing complete! Starting query interface...")
            print("=" * 60 + "\n")
            query_interactive(workspace_id, use_hybrid=use_hybrid)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()

