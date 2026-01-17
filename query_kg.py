#!/usr/bin/env python3
"""
Simple script to query the Knowledge Graph interactively.
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

from core_engine.reasoning import create_reasoner
from core_engine.logging import get_logger

logger = get_logger(__name__)


def query_kg_interactive(workspace_id: str = "default"):
    """Interactive query interface for Knowledge Graph."""
    
    print("=" * 70)
    print("🧠 KNOWLEDGE GRAPH QUERY INTERFACE")
    print("=" * 70)
    print(f"Workspace: {workspace_id}")
    print("\nType your questions below. Type 'quit' or 'exit' to stop.")
    print("=" * 70)
    print()
    
    # Initialize reasoner
    try:
        reasoner = create_reasoner(workspace_id=workspace_id, use_hybrid=True)
        print("✅ Knowledge Graph ready!\n")
    except Exception as e:
        print(f"❌ Error initializing reasoner: {e}")
        return
    
    session_id = None
    
    while True:
        try:
            # Get user input
            question = input("❓ Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            print("\n🔍 Searching Knowledge Graph...\n")
            
            # Query
            try:
                result = reasoner.query(
                    question=question,
                    session_id=session_id
                )
                
                # Store session_id for context
                if not session_id:
                    session_id = result.get('session_id')
                
                # Display answer
                print("=" * 70)
                print("💡 ANSWER:")
                print("=" * 70)
                print(result.get('answer', 'No answer generated.'))
                print()
                
                # Display sources if available
                if result.get('sources'):
                    print("📚 SOURCES:")
                    for i, source in enumerate(result.get('sources', [])[:5], 1):
                        source_info = []
                        if source.get('episode_id'):
                            source_info.append(f"Episode: {source['episode_id']}")
                        if source.get('timestamp'):
                            source_info.append(f"Time: {source['timestamp']}")
                        if source.get('speaker'):
                            source_info.append(f"Speaker: {source['speaker']}")
                        
                        print(f"  {i}. {source.get('text', '')[:200]}...")
                        if source_info:
                            print(f"     ({', '.join(source_info)})")
                    print()
                
                # Display metadata with clear RAG/KG breakdown
                metadata = result.get('metadata', {})
                if metadata:
                    rag_count = metadata.get('rag_count', 0) or len(metadata.get('rag_results', []))
                    kg_count = metadata.get('kg_count', 0) or len(metadata.get('kg_results', []))
                    method = metadata.get('method', 'unknown')
                    
                    print("=" * 70)
                    print("📊 QUERY BREAKDOWN:")
                    print("=" * 70)
                    print(f"  📄 RAG Results: {rag_count}")
                    print(f"  🕸️  KG Results: {kg_count}")
                    print()
                    
                    # Determine answer type
                    if rag_count > 0 and kg_count > 0:
                        answer_type = "🔀 HYBRID (RAG + KG)"
                        print(f"  {answer_type}")
                        print(f"  → Answer synthesized from {rag_count} RAG results + {kg_count} KG results")
                    elif rag_count > 0 and kg_count == 0:
                        answer_type = "📄 PURE RAG"
                        print(f"  {answer_type}")
                        print(f"  → Answer based on {rag_count} RAG results only (no KG matches)")
                    elif rag_count == 0 and kg_count > 0:
                        answer_type = "🕸️  PURE KG"
                        print(f"  {answer_type}")
                        print(f"  → Answer based on {kg_count} KG results only (no RAG matches)")
                    else:
                        answer_type = "❓ NO RESULTS"
                        print(f"  {answer_type}")
                        print(f"  → No matching results found in RAG or KG")
                    
                    if method and method != 'unknown':
                        print(f"  Method: {method}")
                    print()
                
            except Exception as e:
                print(f"❌ Error querying: {e}")
                logger.exception("Query error")
            
            print("=" * 70)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception("Unexpected error")
    
    # Cleanup
    try:
        reasoner.close()
    except:
        pass


def query_single(question: str, workspace_id: str = "default"):
    """Query a single question and return result."""
    
    print(f"🔍 Querying: {question}\n")
    
    try:
        reasoner = create_reasoner(workspace_id=workspace_id, use_hybrid=True)
        
        result = reasoner.query(
            question=question
        )
        
        print("=" * 70)
        print("💡 ANSWER:")
        print("=" * 70)
        print(result.get('answer', 'No answer generated.'))
        print()
        
        # Display sources
        if result.get('sources'):
            print("📚 SOURCES:")
            for i, source in enumerate(result.get('sources', [])[:5], 1):
                source_info = []
                if source.get('episode_id'):
                    source_info.append(f"Episode: {source['episode_id']}")
                if source.get('timestamp'):
                    source_info.append(f"Time: {source['timestamp']}")
                if source.get('speaker'):
                    source_info.append(f"Speaker: {source['speaker']}")
                
                print(f"  {i}. {source.get('text', '')[:200]}...")
                if source_info:
                    print(f"     ({', '.join(source_info)})")
            print()
        
        # Display metadata with clear RAG/KG breakdown
        metadata = result.get('metadata', {})
        if metadata:
            rag_count = metadata.get('rag_count', 0) or len(metadata.get('rag_results', []))
            kg_count = metadata.get('kg_count', 0) or len(metadata.get('kg_results', []))
            method = metadata.get('method', 'unknown')
            
            print("=" * 70)
            print("📊 QUERY BREAKDOWN:")
            print("=" * 70)
            print(f"  📄 RAG Results: {rag_count}")
            print(f"  🕸️  KG Results: {kg_count}")
            print()
            
            # Determine answer type
            if rag_count > 0 and kg_count > 0:
                answer_type = "🔀 HYBRID (RAG + KG)"
                print(f"  {answer_type}")
                print(f"  → Answer synthesized from {rag_count} RAG results + {kg_count} KG results")
            elif rag_count > 0 and kg_count == 0:
                answer_type = "📄 PURE RAG"
                print(f"  {answer_type}")
                print(f"  → Answer based on {rag_count} RAG results only (no KG matches)")
            elif rag_count == 0 and kg_count > 0:
                answer_type = "🕸️  PURE KG"
                print(f"  {answer_type}")
                print(f"  → Answer based on {kg_count} KG results only (no RAG matches)")
            else:
                answer_type = "❓ NO RESULTS"
                print(f"  {answer_type}")
                print(f"  → No matching results found in RAG or KG")
            
            if method and method != 'unknown':
                print(f"  Method: {method}")
            print()
        
        reasoner.close()
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query the Knowledge Graph"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        help="Single question to ask (if not provided, starts interactive mode)"
    )
    parser.add_argument(
        "--workspace-id",
        default=os.getenv("WORKSPACE_ID", "default"),
        help="Workspace identifier"
    )
    
    args = parser.parse_args()
    
    if args.question:
        # Single question mode
        query_single(args.question, args.workspace_id)
    else:
        # Interactive mode
        query_kg_interactive(args.workspace_id)

