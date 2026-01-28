"""
Simple API Test: No Results Rejection

Tests queries via the API endpoint to verify RAG=0, KG=0 rejection.
"""
import requests
import json
from test_no_results_rejection import TEST_QUERIES, VALID_QUERIES

API_URL = "http://localhost:8000/api/v1/query"

def test_query_via_api(query: str, should_reject: bool = True):
    """Test a query via API."""
    try:
        response = requests.post(
            API_URL,
            json={
                "question": query,
                "session_id": "test_session",
            },
            headers={"X-Workspace-Id": "default"},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ ERROR | HTTP {response.status_code} | {query[:60]}")
            return False
        
        data = response.json()
        answer = data.get("answer", "")
        metadata = data.get("metadata", {})
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
        
    except requests.exceptions.ConnectionError:
        print(f"⚠️  SKIP  | Backend not running | {query[:60]}")
        print("      Start backend: cd backend && uv run uvicorn app.main:app --reload")
        return None
    except Exception as e:
        print(f"❌ ERROR | {query[:60]}")
        print(f"      Error: {str(e)}")
        return False

def run_tests():
    """Run all tests."""
    print("=" * 80)
    print("TESTING: No Results Rejection (RAG=0, KG=0) via API")
    print("=" * 80)
    print(f"\nAPI URL: {API_URL}")
    print("Make sure backend is running!\n")
    
    print("=" * 80)
    print("TEST QUERIES - Should be REJECTED")
    print("=" * 80)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for query in TEST_QUERIES[:10]:  # Test first 10 for quick check
        result = test_query_via_api(query, should_reject=True)
        if result is True:
            passed += 1
        elif result is False:
            failed += 1
        else:
            skipped += 1
    
    print("\n" + "=" * 80)
    print("VALID QUERIES - Should be ALLOWED")
    print("=" * 80)
    
    for query in VALID_QUERIES[:3]:  # Test first 3
        result = test_query_via_api(query, should_reject=False)
        if result is True:
            passed += 1
        elif result is False:
            failed += 1
        else:
            skipped += 1
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Tested: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    if passed + failed > 0:
        print(f"Pass Rate: {passed / (passed + failed) * 100:.1f}%")
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
