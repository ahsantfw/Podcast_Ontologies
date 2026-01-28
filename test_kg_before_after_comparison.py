"""
Before/After Comparison Test for KG Query Optimizer

Compares baseline KG search vs optimized KG search.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.reasoning.kg_query_optimizer import KGQueryOptimizer
from core_engine.logging import get_logger

logger = get_logger(__name__)


class KGBeforeAfterTester:
    """Compare baseline vs optimized KG search."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        
        # Initialize Neo4j client
        self.neo4j_client = Neo4jClient(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )
        
        # Initialize optimizer
        self.optimizer = KGQueryOptimizer(
            neo4j_client=self.neo4j_client,
            openai_client=None,  # Skip LLM for faster testing
            workspace_id=workspace_id,
        )
        
        # Test queries
        self.test_queries = [
            {
                "query": "What did Phil say about meditation?",
                "type": "entity_linking",
                "description": "Entity linking: 'Phil' should map to 'Phil Jackson'"
            },
            {
                "query": "What practices lead to better decision-making?",
                "type": "multi_hop",
                "description": "Multi-hop: Practices → Outcomes → Decision-making"
            },
            {
                "query": "What concepts appear in multiple episodes?",
                "type": "cross_episode",
                "description": "Cross-episode: Find concepts with episode_ids.length >= 2"
            },
            {
                "query": "How does meditation relate to creativity?",
                "type": "multi_hop",
                "description": "Multi-hop: Find relationships between concepts"
            },
            {
                "query": "What practices optimize clarity?",
                "type": "multi_hop",
                "description": "Multi-hop: Practices → OPTIMIZES → Clarity"
            },
        ]
    
    def baseline_search(self, query: str) -> List[Dict[str, Any]]:
        """Baseline KG search (current implementation)."""
        words = query.lower().split()
        stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why", "does", "do", "did", "this", "that", "about", "for", "with", "from"}
        search_terms = [w for w in words if len(w) > 2 and w not in stop_words]
        
        if query.lower().strip():
            search_terms = [query.lower().strip()] + search_terms
        
        search_terms = search_terms[:3]
        
        if not search_terms:
            return []
        
        cypher = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (
            ANY(term IN $search_terms WHERE toLower(c.name) CONTAINS term)
            OR ANY(term IN $search_terms WHERE toLower(c.description) CONTAINS term)
          )
        OPTIONAL MATCH (c)-[r]->(related)
        WHERE related.workspace_id = $workspace_id
        WITH DISTINCT c, collect(DISTINCT {rel: type(r), target: related.name})[..5] as relationships
        RETURN c.name as concept, 
               labels(c)[0] as type,
               c.description as description,
               relationships,
               CASE 
                 WHEN ANY(term IN $search_terms WHERE toLower(c.name) = term) THEN 1
                 WHEN ANY(term IN $search_terms WHERE toLower(c.name) STARTS WITH term) THEN 2
                 ELSE 3
               END as relevance
        ORDER BY relevance
        LIMIT 10
        """
        
        try:
            results = self.neo4j_client.execute_read(
                cypher,
                {"workspace_id": self.workspace_id, "search_terms": search_terms}
            )
            return results or []
        except Exception as e:
            logger.error(f"Baseline search failed: {e}", exc_info=True)
            return []
    
    def test_before(self) -> Dict[str, Any]:
        """Test baseline (before optimizer)."""
        print("\n" + "=" * 80)
        print("TESTING BEFORE (BASELINE)")
        print("=" * 80)
        
        results = {
            "timestamp": time.time(),
            "queries": [],
            "summary": {
                "total_queries": len(self.test_queries),
                "total_latency_ms": 0,
                "avg_latency_ms": 0,
                "total_kg_results": 0,
                "avg_kg_results": 0,
                "queries_with_results": 0,
                "queries_with_zero_results": 0,
            }
        }
        
        for i, test_case in enumerate(self.test_queries, 1):
            query = test_case["query"]
            print(f"\n[{i}/{len(self.test_queries)}] {query}")
            
            start_time = time.time()
            kg_results = self.baseline_search(query)
            latency_ms = (time.time() - start_time) * 1000
            
            kg_count = len(kg_results) if kg_results else 0
            
            print(f"  → Results: {kg_count}")
            print(f"  → Latency: {latency_ms:.2f}ms")
            
            if kg_results:
                print(f"  → First: {kg_results[0].get('concept', 'N/A')}")
            
            results["queries"].append({
                "query": query,
                "type": test_case["type"],
                "description": test_case["description"],
                "kg_count": kg_count,
                "latency_ms": latency_ms,
            })
            
            results["summary"]["total_latency_ms"] += latency_ms
            results["summary"]["total_kg_results"] += kg_count
            if kg_count > 0:
                results["summary"]["queries_with_results"] += 1
            else:
                results["summary"]["queries_with_zero_results"] += 1
        
        results["summary"]["avg_latency_ms"] = results["summary"]["total_latency_ms"] / len(self.test_queries)
        results["summary"]["avg_kg_results"] = results["summary"]["total_kg_results"] / len(self.test_queries)
        
        print("\n" + "=" * 80)
        print("BEFORE SUMMARY")
        print("=" * 80)
        print(f"Total Queries: {results['summary']['total_queries']}")
        print(f"Avg Latency: {results['summary']['avg_latency_ms']:.2f}ms")
        print(f"Avg KG Results: {results['summary']['avg_kg_results']:.2f}")
        print(f"Queries with Results: {results['summary']['queries_with_results']}")
        print(f"Queries with Zero Results: {results['summary']['queries_with_zero_results']}")
        
        return results
    
    def test_after(self) -> Dict[str, Any]:
        """Test with optimizer (after)."""
        print("\n" + "=" * 80)
        print("TESTING AFTER (WITH OPTIMIZER)")
        print("=" * 80)
        
        results = {
            "timestamp": time.time(),
            "queries": [],
            "summary": {
                "total_queries": len(self.test_queries),
                "total_latency_ms": 0,
                "avg_latency_ms": 0,
                "total_kg_results": 0,
                "avg_kg_results": 0,
                "queries_with_results": 0,
                "queries_with_zero_results": 0,
            }
        }
        
        for i, test_case in enumerate(self.test_queries, 1):
            query = test_case["query"]
            query_type = test_case["type"]
            print(f"\n[{i}/{len(self.test_queries)}] {query}")
            print(f"  Type: {query_type}")
            
            start_time = time.time()
            kg_results = self.optimizer.search(
                query=query,
                query_type=query_type,
                limit=10,
            )
            latency_ms = (time.time() - start_time) * 1000
            
            kg_count = len(kg_results) if kg_results else 0
            
            print(f"  → Results: {kg_count}")
            print(f"  → Latency: {latency_ms:.2f}ms")
            
            if kg_results:
                first_result = kg_results[0].get('concept') or kg_results[0].get('name') or kg_results[0].get('source_concept', 'N/A')
                print(f"  → First: {first_result}")
            
            results["queries"].append({
                "query": query,
                "type": query_type,
                "description": test_case["description"],
                "kg_count": kg_count,
                "latency_ms": latency_ms,
            })
            
            results["summary"]["total_latency_ms"] += latency_ms
            results["summary"]["total_kg_results"] += kg_count
            if kg_count > 0:
                results["summary"]["queries_with_results"] += 1
            else:
                results["summary"]["queries_with_zero_results"] += 1
        
        results["summary"]["avg_latency_ms"] = results["summary"]["total_latency_ms"] / len(self.test_queries)
        results["summary"]["avg_kg_results"] = results["summary"]["total_kg_results"] / len(self.test_queries)
        
        print("\n" + "=" * 80)
        print("AFTER SUMMARY")
        print("=" * 80)
        print(f"Total Queries: {results['summary']['total_queries']}")
        print(f"Avg Latency: {results['summary']['avg_latency_ms']:.2f}ms")
        print(f"Avg KG Results: {results['summary']['avg_kg_results']:.2f}")
        print(f"Queries with Results: {results['summary']['queries_with_results']}")
        print(f"Queries with Zero Results: {results['summary']['queries_with_zero_results']}")
        
        return results
    
    def compare(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Compare before/after results."""
        print("\n" + "=" * 80)
        print("COMPARISON: BEFORE vs AFTER")
        print("=" * 80)
        
        comparison = {
            "latency": {
                "before_avg_ms": before["summary"]["avg_latency_ms"],
                "after_avg_ms": after["summary"]["avg_latency_ms"],
                "change_ms": after["summary"]["avg_latency_ms"] - before["summary"]["avg_latency_ms"],
                "change_pct": (
                    (after["summary"]["avg_latency_ms"] - before["summary"]["avg_latency_ms"])
                    / before["summary"]["avg_latency_ms"] * 100
                    if before["summary"]["avg_latency_ms"] > 0 else 0
                ),
            },
            "kg_results": {
                "before_avg": before["summary"]["avg_kg_results"],
                "after_avg": after["summary"]["avg_kg_results"],
                "improvement": after["summary"]["avg_kg_results"] - before["summary"]["avg_kg_results"],
                "improvement_pct": (
                    (after["summary"]["avg_kg_results"] - before["summary"]["avg_kg_results"])
                    / before["summary"]["avg_kg_results"] * 100
                    if before["summary"]["avg_kg_results"] > 0 else float('inf')
                ),
            },
            "coverage": {
                "before_with_results": before["summary"]["queries_with_results"],
                "after_with_results": after["summary"]["queries_with_results"],
                "improvement": after["summary"]["queries_with_results"] - before["summary"]["queries_with_results"],
            },
            "query_by_query": [],
        }
        
        for before_q, after_q in zip(before["queries"], after["queries"]):
            comparison["query_by_query"].append({
                "query": before_q["query"],
                "type": before_q["type"],
                "before_kg_count": before_q["kg_count"],
                "after_kg_count": after_q["kg_count"],
                "kg_improvement": after_q["kg_count"] - before_q["kg_count"],
                "before_latency_ms": before_q["latency_ms"],
                "after_latency_ms": after_q["latency_ms"],
                "latency_change_ms": after_q["latency_ms"] - before_q["latency_ms"],
            })
        
        print("\nLATENCY:")
        print(f"  Before Avg: {comparison['latency']['before_avg_ms']:.2f}ms")
        print(f"  After Avg: {comparison['latency']['after_avg_ms']:.2f}ms")
        print(f"  Change: {comparison['latency']['change_ms']:+.2f}ms ({comparison['latency']['change_pct']:+.1f}%)")
        
        print("\nKG RESULTS:")
        print(f"  Before Avg: {comparison['kg_results']['before_avg']:.2f}")
        print(f"  After Avg: {comparison['kg_results']['after_avg']:.2f}")
        print(f"  Improvement: +{comparison['kg_results']['improvement']:.2f} ({comparison['kg_results']['improvement_pct']:.1f}%)")
        
        print("\nCOVERAGE:")
        print(f"  Before: {comparison['coverage']['before_with_results']}/{len(self.test_queries)} queries had results")
        print(f"  After: {comparison['coverage']['after_with_results']}/{len(self.test_queries)} queries had results")
        print(f"  Improvement: +{comparison['coverage']['improvement']} queries")
        
        print("\nQUERY-BY-QUERY COMPARISON:")
        for qc in comparison["query_by_query"]:
            print(f"\n  Query: {qc['query']}")
            print(f"    Type: {qc['type']}")
            print(f"    KG Count: {qc['before_kg_count']} → {qc['after_kg_count']} (+{qc['kg_improvement']})")
            print(f"    Latency: {qc['before_latency_ms']:.2f}ms → {qc['after_latency_ms']:.2f}ms ({qc['latency_change_ms']:+.2f}ms)")
        
        return comparison
    
    def save_results(self, before: Dict[str, Any], after: Dict[str, Any], comparison: Dict[str, Any]):
        """Save results to JSON."""
        results = {
            "before": before,
            "after": after,
            "comparison": comparison,
            "timestamp": time.time(),
        }
        
        filepath = project_root / "metrics" / "kg_optimizer_comparison.json"
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Results saved to: {filepath}")


def main():
    """Run before/after comparison."""
    print("=" * 80)
    print("KG QUERY OPTIMIZER - BEFORE/AFTER COMPARISON")
    print("=" * 80)
    
    tester = KGBeforeAfterTester(workspace_id="default")
    
    # Run before test
    before_results = tester.test_before()
    
    # Run after test
    after_results = tester.test_after()
    
    # Compare
    comparison = tester.compare(before_results, after_results)
    
    # Save results
    tester.save_results(before_results, after_results, comparison)
    
    print("\n" + "=" * 80)
    print("✅ COMPARISON COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
