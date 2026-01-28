"""
Automated Test: No Results Rejection

Tests that queries with RAG=0, KG=0 are properly rejected.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from test_no_results_rejection import TEST_QUERIES, VALID_QUERIES

def test_query(query: str, should_reject: bool = True):
    """Test a single query."""
    from core_engine.reasoning.reasoning import KGReasoner
    from core_engine.reasoning.hybrid_retriever import HybridRetriever
    from core_engine.kg.neo4j_client import get_neo4j_client
    
    try:
        # Initialize reasoner (KGReasoner creates HybridRetriever internally)
        reasoner = KGReasoner(
            workspace_id="test",
        )
        
        # Query
        result = reasoner.query(question=query, session_id="test_session")
        
        answer = result.get("answer", "")
        metadata = result.get("metadata", {})
        rag_count = metadata.get("rag_count", 0)
        kg_count = metadata.get("kg_count", 0)
        
        # Check if rejected
        is_rejected = "couldn't find information" in answer.lower() or "I couldn't find" in answer
        
        # Determine result
        if should_reject:
            if is_rejected:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
        else:
            if not is_rejected:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
        
        print(f"{status} | RAG: {rag_count:2d} | KG: {kg_count:2d} | {query[:60]}")
        
        if should_reject and not is_rejected:
            print(f"      Expected rejection but got: {answer[:100]}...")
        
        return is_rejected == should_reject
        
    except Exception as e:
        print(f"❌ ERROR | {query[:60]}")
        print(f"      Error: {str(e)}")
        return False

def run_tests():
    """Run all tests."""
    print("=" * 80)
    print("TESTING: No Results Rejection (RAG=0, KG=0)")
    print("=" * 80)
    
    print("\n" + "=" * 80)
    print("TEST QUERIES - Should be REJECTED")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for query in TEST_QUERIES:
        if test_query(query, should_reject=True):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print("VALID QUERIES - Should be ALLOWED")
    print("=" * 80)
    
    for query in VALID_QUERIES:
        if test_query(query, should_reject=False):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total: {len(TEST_QUERIES) + len(VALID_QUERIES)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {passed / (len(TEST_QUERIES) + len(VALID_QUERIES)) * 100:.1f}%")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
