"""
Test Suite: No Results Rejection (RAG=0, KG=0)

Tests 50 queries that should be REJECTED when RAG=0, KG=0.
These are general knowledge questions, out-of-scope queries, or questions
not related to podcast content.

Expected Behavior: All should return "I couldn't find information about that..."
"""

TEST_QUERIES = [
    # General Knowledge Questions (Should be rejected)
    "What is RAG?",
    "What is Retrieval Augmented Generation?",
    "Do you know Urdu?",
    "Can you translate Me acha hu into English?",
    "What are the issues of society?",
    "What are the main problems in society?",
    "What are solutions to social problems?",
    "What is the meaning of life?",
    "What is philosophy?",
    "What is creativity?",
    "What is meditation?",
    "What is mindfulness?",
    "What is coaching?",
    "What is personal development?",
    
    # Technical/Programming Questions (Should be rejected)
    "How do I write a Python function?",
    "What is machine learning?",
    "What is artificial intelligence?",
    "How does a neural network work?",
    "What is the difference between Python and JavaScript?",
    "How do I deploy a web application?",
    
    # Math Questions (Should be rejected)
    "What is 2+2?",
    "Solve for x: 3x + 7 = 25",
    "What is the square root of 16?",
    "Calculate the area of a circle with radius 5",
    
    # Current Events/News (Should be rejected)
    "What happened today?",
    "What is the latest news?",
    "What is happening in the world?",
    "What are current events?",
    
    # Weather/Geography (Should be rejected)
    "What is the weather today?",
    "What is the capital of France?",
    "Where is Mount Everest?",
    "What is the population of India?",
    
    # General Definitions (Should be rejected - not podcast-specific)
    "What does success mean?",
    "What is happiness?",
    "What is love?",
    "What is failure?",
    "What is leadership?",
    "What is teamwork?",
    
    # Language/Translation (Should be rejected)
    "Translate hello to Spanish",
    "What does bonjour mean?",
    "How do you say thank you in French?",
    
    # General "How to" Questions (Should be rejected - not podcast-specific)
    "How do I become successful?",
    "How do I improve my life?",
    "How do I find my purpose?",
    "How do I be happy?",
    
    # Meta Questions About System (Should be rejected - not podcast content)
    "What can you do?",
    "How do you work?",
    "What is your purpose?",
    "Who created you?",
    
    # Week/Topic References (Should be rejected - not podcast content)
    "Week 1: Query Expansion",
    "What is Week 1 about?",
    "Tell me about Phase 2",
]

# Queries that SHOULD work (for comparison)
VALID_QUERIES = [
    # Greetings (Don't need results)
    "Hi",
    "Hello",
    "Hey",
    "Thanks",
    "Thank you",
    
    # Podcast-specific queries (Should work if RAG/KG has results)
    "Who is Phil Jackson?",
    "What did Phil Jackson say about meditation?",
    "What concepts are in the podcasts?",
    "What practices lead to better decision-making?",
    "What did speakers say about creativity?",
]

def print_test_queries():
    """Print test queries in a format suitable for testing."""
    print("=" * 80)
    print("TEST QUERIES - Should be REJECTED (RAG=0, KG=0)")
    print("=" * 80)
    print(f"\nTotal: {len(TEST_QUERIES)} queries\n")
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"{i:2d}. {query}")
    
    print("\n" + "=" * 80)
    print("VALID QUERIES - Should be ALLOWED")
    print("=" * 80)
    print(f"\nTotal: {len(VALID_QUERIES)} queries\n")
    
    for i, query in enumerate(VALID_QUERIES, 1):
        print(f"{i:2d}. {query}")

def create_test_script():
    """Create a Python test script to run these queries."""
    script = '''"""
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
    from core_engine.retrieval.hybrid_retriever import HybridRetriever
    from core_engine.kg.neo4j_client import get_neo4j_client
    
    try:
        # Initialize reasoner
        neo4j_client = get_neo4j_client()
        hybrid_retriever = HybridRetriever(
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            neo4j_client=neo4j_client,
        )
        
        reasoner = KGReasoner(
            neo4j_client=neo4j_client,
            hybrid_retriever=hybrid_retriever,
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
'''
    return script

if __name__ == "__main__":
    print_test_queries()
    
    # Create test script file
    script_content = create_test_script()
    with open("run_no_results_test.py", "w") as f:
        f.write(script_content)
    
    print("\n" + "=" * 80)
    print("Test script created: run_no_results_test.py")
    print("Run with: uv run python run_no_results_test.py")
    print("=" * 80)
