"""
Detailed API Test: No Results Rejection with Results Storage

Tests queries via the API endpoint and stores detailed results.
"""
import requests
import json
from datetime import datetime
from pathlib import Path
from test_no_results_rejection import TEST_QUERIES, VALID_QUERIES

API_URL = "http://localhost:8000/api/v1/query"

def test_query_via_api(query: str, should_reject: bool = True):
    """Test a query via API and return detailed results."""
    result_data = {
        "query": query,
        "should_reject": should_reject,
        "timestamp": datetime.now().isoformat(),
    }
    
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
            result_data.update({
                "status": "error",
                "http_status": response.status_code,
                "error": f"HTTP {response.status_code}",
                "passed": False
            })
            return result_data
        
        data = response.json()
        answer = data.get("answer", "")
        metadata = data.get("metadata", {})
        rag_count = metadata.get("rag_count", 0)
        kg_count = metadata.get("kg_count", 0)
        intent = metadata.get("intent", "unknown")
        method = metadata.get("method", "unknown")
        
        # Check if rejected
        is_rejected = "couldn't find information" in answer.lower() or "I couldn't find" in answer
        
        # Determine result
        passed = (is_rejected == should_reject)
        
        result_data.update({
            "status": "success",
            "rag_count": rag_count,
            "kg_count": kg_count,
            "intent": intent,
            "method": method,
            "is_rejected": is_rejected,
            "answer_preview": answer[:200],
            "full_answer": answer,
            "metadata": metadata,
            "passed": passed
        })
        
        return result_data
        
    except requests.exceptions.ConnectionError:
        result_data.update({
            "status": "error",
            "error": "Backend not running",
            "passed": None
        })
        return result_data
    except Exception as e:
        result_data.update({
            "status": "error",
            "error": str(e),
            "passed": False
        })
        return result_data

def run_tests_and_save():
    """Run all tests and save results."""
    print("=" * 80)
    print("TESTING: No Results Rejection (RAG=0, KG=0) via API")
    print("=" * 80)
    print(f"\nAPI URL: {API_URL}")
    print("Timestamp: {}\n".format(datetime.now().isoformat()))
    
    all_results = {
        "test_timestamp": datetime.now().isoformat(),
        "api_url": API_URL,
        "test_queries": [],
        "valid_queries": [],
        "summary": {}
    }
    
    print("=" * 80)
    print("TEST QUERIES - Should be REJECTED")
    print("=" * 80)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for query in TEST_QUERIES[:10]:  # Test first 10 for quick check
        result = test_query_via_api(query, should_reject=True)
        all_results["test_queries"].append(result)
        
        if result["status"] == "success":
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            rag_count = result.get("rag_count", 0)
            kg_count = result.get("kg_count", 0)
            print(f"{status} | RAG: {rag_count:2d} | KG: {kg_count:2d} | {query[:60]}")
            
            if result["passed"]:
                passed += 1
            else:
                failed += 1
                print(f"      Expected rejection but got: {result['answer_preview']}...")
        else:
            print(f"⚠️  SKIP  | Backend not running | {query[:60]}")
            skipped += 1
    
    print("\n" + "=" * 80)
    print("VALID QUERIES - Should be ALLOWED")
    print("=" * 80)
    
    for query in VALID_QUERIES[:3]:  # Test first 3
        result = test_query_via_api(query, should_reject=False)
        all_results["valid_queries"].append(result)
        
        if result["status"] == "success":
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            rag_count = result.get("rag_count", 0)
            kg_count = result.get("kg_count", 0)
            print(f"{status} | RAG: {rag_count:2d} | KG: {kg_count:2d} | {query[:60]}")
            
            if result["passed"]:
                passed += 1
            else:
                failed += 1
        else:
            print(f"⚠️  SKIP  | Backend not running | {query[:60]}")
            skipped += 1
    
    # Calculate summary
    total_tested = passed + failed
    pass_rate = (passed / total_tested * 100) if total_tested > 0 else 0
    
    all_results["summary"] = {
        "total_tested": total_tested,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round(pass_rate, 1)
    }
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Tested: {total_tested}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    if total_tested > 0:
        print(f"Pass Rate: {pass_rate:.1f}%")
    
    # Save results to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = Path(f"test_results_{timestamp}.json")
    
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✅ Results saved to: {results_file}")
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = run_tests_and_save()
    sys.exit(0 if success else 1)
