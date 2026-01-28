"""
Simple KG Query Optimizer Test

Tests the optimizer directly without requiring full agent setup.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def test_kg_optimizer():
    """Test KG Query Optimizer functionality."""
    print("=" * 80)
    print("TESTING KG QUERY OPTIMIZER")
    print("=" * 80)
    
    try:
        from core_engine.kg.neo4j_client import Neo4jClient
        from core_engine.reasoning.kg_query_optimizer import KGQueryOptimizer
        
        # Initialize Neo4j client
        neo4j_client = Neo4jClient(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )
        
        # Initialize optimizer
        optimizer = KGQueryOptimizer(
            neo4j_client=neo4j_client,
            openai_client=None,  # Skip LLM for now
            workspace_id="default",
        )
        
        print("\n✅ KG Query Optimizer initialized successfully!")
        
        # Test queries
        test_queries = [
            ("What did Phil say about meditation?", "entity_linking"),
            ("What practices lead to better decision-making?", "multi_hop"),
            ("What concepts appear in multiple episodes?", "cross_episode"),
            ("How does meditation relate to creativity?", "multi_hop"),
        ]
        
        print("\n" + "=" * 80)
        print("TESTING QUERIES")
        print("=" * 80)
        
        for query, query_type in test_queries:
            print(f"\n📝 Query: {query}")
            print(f"   Type: {query_type}")
            
            try:
                results = optimizer.search(
                    query=query,
                    query_type=query_type,
                    limit=5,
                )
                
                result_count = len(results) if results else 0
                print(f"   ✅ Results: {result_count}")
                
                if results:
                    print(f"   📊 First result: {results[0].get('concept', results[0].get('name', 'N/A'))}")
                else:
                    print(f"   ⚠️  No results found")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("Make sure all dependencies are installed.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_kg_optimizer()
