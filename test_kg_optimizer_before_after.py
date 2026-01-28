"""
Comprehensive Before/After Test for KG Query Optimizer

Tests accuracy, latency, and improvements:
- Entity Linking (aliases, variations)
- Multi-Hop Queries (2-3 hops)
- Cross-Episode Queries (concepts across episodes)
"""

import os
import sys
import time
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import json for JSON serialization
import json as json_module

from dotenv import load_dotenv
load_dotenv()

from core_engine.reasoning.agent import PodcastAgent
from core_engine.reasoning.hybrid_retriever import HybridRetriever
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger
from openai import OpenAI

logger = get_logger(__name__)


class KGOptimizerTester:
    """Test KG Query Optimizer before/after implementation."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize components
        self.neo4j_client = Neo4jClient(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )
        
        self.hybrid_retriever = HybridRetriever(
            workspace_id=workspace_id,
            qdrant_client=None,  # Not needed for KG-only tests
            neo4j_client=self.neo4j_client,
            openai_client=self.openai_client,
        )
        
        self.agent = PodcastAgent(
            workspace_id=workspace_id,
            hybrid_retriever=self.hybrid_retriever,
            neo4j_client=self.neo4j_client,
            openai_client=self.openai_client,
        )
        
        # Test queries covering different scenarios
        self.test_queries = [
            # Entity Linking Tests
            {
                "query": "What did Phil say about meditation?",
                "expected_entities": ["Phil Jackson", "PJ", "meditation"],
                "test_type": "entity_linking",
                "description": "Entity linking: 'Phil' should map to 'Phil Jackson'"
            },
            {
                "query": "What practices does Joe Dispenza recommend?",
                "expected_entities": ["Joe Dispenza", "practices"],
                "test_type": "entity_linking",
                "description": "Entity linking: Full name should be found"
            },
            
            # Multi-Hop Tests
            {
                "query": "What practices lead to better decision-making?",
                "expected_entities": ["practices", "decision-making"],
                "test_type": "multi_hop",
                "description": "Multi-hop: Practices → Outcomes → Decision-making (2-3 hops)"
            },
            {
                "query": "How does meditation relate to creativity?",
                "expected_entities": ["meditation", "creativity"],
                "test_type": "multi_hop",
                "description": "Multi-hop: Find relationships between two concepts"
            },
            {
                "query": "What practices optimize clarity?",
                "expected_entities": ["practices", "clarity"],
                "test_type": "multi_hop",
                "description": "Multi-hop: Practices → OPTIMIZES → Clarity"
            },
            
            # Cross-Episode Tests
            {
                "query": "What concepts appear in multiple episodes?",
                "expected_entities": [],
                "test_type": "cross_episode",
                "description": "Cross-episode: Find concepts with episode_ids.length >= 2"
            },
            {
                "query": "What did multiple speakers say about creativity?",
                "expected_entities": ["creativity"],
                "test_type": "cross_episode",
                "description": "Cross-episode: Find creativity across episodes"
            },
            
            # Complex Queries
            {
                "query": "What practices improve mental health outcomes?",
                "expected_entities": ["practices", "mental health"],
                "test_type": "complex",
                "description": "Complex: Multi-hop + entity linking"
            },
            {
                "query": "How does reflection relate to decision-making quality?",
                "expected_entities": ["reflection", "decision-making"],
                "test_type": "complex",
                "description": "Complex: Multi-hop relationship query"
            },
        ]
    
    def test_before(self) -> Dict[str, Any]:
        """Test current KG search (before optimizer)."""
        logger.info("=" * 80)
        logger.info("TESTING BEFORE KG OPTIMIZER")
        logger.info("=" * 80)
        
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
            logger.info(f"\n[{i}/{len(self.test_queries)}] Testing: {query}")
            logger.info(f"Type: {test_case['test_type']}")
            logger.info(f"Description: {test_case['description']}")
            
            # Measure latency
            start_time = time.time()
            
            # Use current KG search method
            kg_results = self.agent._search_knowledge_graph(query)
            
            latency_ms = (time.time() - start_time) * 1000
            
            kg_count = len(kg_results) if kg_results else 0
            
            # Log results
            logger.info(f"  → KG Results: {kg_count}")
            logger.info(f"  → Latency: {latency_ms:.2f}ms")
            
            if kg_results:
                logger.info(f"  → First result: {kg_results[0].get('concept', 'N/A')}")
            
            # Store results
            query_result = {
                "query": query,
                "test_type": test_case["test_type"],
                "description": test_case["description"],
                "kg_count": kg_count,
                "latency_ms": latency_ms,
                "kg_results": kg_results[:3] if kg_results else [],  # Store first 3 for analysis
                "expected_entities": test_case.get("expected_entities", []),
            }
            
            results["queries"].append(query_result)
            
            # Update summary
            results["summary"]["total_latency_ms"] += latency_ms
            results["summary"]["total_kg_results"] += kg_count
            if kg_count > 0:
                results["summary"]["queries_with_results"] += 1
            else:
                results["summary"]["queries_with_zero_results"] += 1
        
        # Calculate averages
        results["summary"]["avg_latency_ms"] = (
            results["summary"]["total_latency_ms"] / len(self.test_queries)
        )
        results["summary"]["avg_kg_results"] = (
            results["summary"]["total_kg_results"] / len(self.test_queries)
        )
        
        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("BEFORE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Queries: {results['summary']['total_queries']}")
        logger.info(f"Avg Latency: {results['summary']['avg_latency_ms']:.2f}ms")
        logger.info(f"Avg KG Results: {results['summary']['avg_kg_results']:.2f}")
        logger.info(f"Queries with Results: {results['summary']['queries_with_results']}")
        logger.info(f"Queries with Zero Results: {results['summary']['queries_with_zero_results']}")
        
        return results
    
    def test_after(self, kg_optimizer) -> Dict[str, Any]:
        """Test KG search with optimizer (after implementation)."""
        logger.info("\n" + "=" * 80)
        logger.info("TESTING AFTER KG OPTIMIZER")
        logger.info("=" * 80)
        
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
            logger.info(f"\n[{i}/{len(self.test_queries)}] Testing: {query}")
            logger.info(f"Type: {test_case['test_type']}")
            logger.info(f"Description: {test_case['description']}")
            
            # Measure latency
            start_time = time.time()
            
            # Use KG optimizer
            kg_results = kg_optimizer.search(
                query=query,
                query_type=test_case["test_type"],
                workspace_id=self.workspace_id,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            kg_count = len(kg_results) if kg_results else 0
            
            # Log results
            logger.info(f"  → KG Results: {kg_count}")
            logger.info(f"  → Latency: {latency_ms:.2f}ms")
            
            if kg_results:
                logger.info(f"  → First result: {kg_results[0].get('concept', kg_results[0].get('name', 'N/A'))}")
            
            # Store results
            query_result = {
                "query": query,
                "test_type": test_case["test_type"],
                "description": test_case["description"],
                "kg_count": kg_count,
                "latency_ms": latency_ms,
                "kg_results": kg_results[:3] if kg_results else [],
                "expected_entities": test_case.get("expected_entities", []),
            }
            
            results["queries"].append(query_result)
            
            # Update summary
            results["summary"]["total_latency_ms"] += latency_ms
            results["summary"]["total_kg_results"] += kg_count
            if kg_count > 0:
                results["summary"]["queries_with_results"] += 1
            else:
                results["summary"]["queries_with_zero_results"] += 1
        
        # Calculate averages
        results["summary"]["avg_latency_ms"] = (
            results["summary"]["total_latency_ms"] / len(self.test_queries)
        )
        results["summary"]["avg_kg_results"] = (
            results["summary"]["total_kg_results"] / len(self.test_queries)
        )
        
        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("AFTER SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Queries: {results['summary']['total_queries']}")
        logger.info(f"Avg Latency: {results['summary']['avg_latency_ms']:.2f}ms")
        logger.info(f"Avg KG Results: {results['summary']['avg_kg_results']:.2f}")
        logger.info(f"Queries with Results: {results['summary']['queries_with_results']}")
        logger.info(f"Queries with Zero Results: {results['summary']['queries_with_zero_results']}")
        
        return results
    
    def compare_results(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Compare before/after results."""
        logger.info("\n" + "=" * 80)
        logger.info("COMPARISON: BEFORE vs AFTER")
        logger.info("=" * 80)
        
        comparison = {
            "latency": {
                "before_avg_ms": before["summary"]["avg_latency_ms"],
                "after_avg_ms": after["summary"]["avg_latency_ms"],
                "improvement_ms": after["summary"]["avg_latency_ms"] - before["summary"]["avg_latency_ms"],
                "improvement_pct": (
                    (before["summary"]["avg_latency_ms"] - after["summary"]["avg_latency_ms"]) 
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
        
        # Compare each query
        for i, (before_query, after_query) in enumerate(zip(before["queries"], after["queries"])):
            query_comparison = {
                "query": before_query["query"],
                "test_type": before_query["test_type"],
                "before_kg_count": before_query["kg_count"],
                "after_kg_count": after_query["kg_count"],
                "kg_improvement": after_query["kg_count"] - before_query["kg_count"],
                "before_latency_ms": before_query["latency_ms"],
                "after_latency_ms": after_query["latency_ms"],
                "latency_change_ms": after_query["latency_ms"] - before_query["latency_ms"],
            }
            comparison["query_by_query"].append(query_comparison)
        
        # Log comparison
        logger.info("\nLATENCY:")
        logger.info(f"  Before Avg: {comparison['latency']['before_avg_ms']:.2f}ms")
        logger.info(f"  After Avg: {comparison['latency']['after_avg_ms']:.2f}ms")
        logger.info(f"  Change: {comparison['latency']['improvement_ms']:.2f}ms ({comparison['latency']['improvement_pct']:.1f}%)")
        
        logger.info("\nKG RESULTS:")
        logger.info(f"  Before Avg: {comparison['kg_results']['before_avg']:.2f}")
        logger.info(f"  After Avg: {comparison['kg_results']['after_avg']:.2f}")
        logger.info(f"  Improvement: +{comparison['kg_results']['improvement']:.2f} ({comparison['kg_results']['improvement_pct']:.1f}%)")
        
        logger.info("\nCOVERAGE:")
        logger.info(f"  Before: {comparison['coverage']['before_with_results']}/{len(self.test_queries)} queries had results")
        logger.info(f"  After: {comparison['coverage']['after_with_results']}/{len(self.test_queries)} queries had results")
        logger.info(f"  Improvement: +{comparison['coverage']['improvement']} queries")
        
        logger.info("\nQUERY-BY-QUERY COMPARISON:")
        for qc in comparison["query_by_query"]:
            logger.info(f"\n  Query: {qc['query']}")
            logger.info(f"    KG Count: {qc['before_kg_count']} → {qc['after_kg_count']} (+{qc['kg_improvement']})")
            logger.info(f"    Latency: {qc['before_latency_ms']:.2f}ms → {qc['after_latency_ms']:.2f}ms ({qc['latency_change_ms']:+.2f}ms)")
        
        return comparison
    
    def save_results(self, before: Dict[str, Any], after: Dict[str, Any], comparison: Dict[str, Any], filename: str = "kg_optimizer_test_results.json"):
        """Save test results to JSON file."""
        results = {
            "before": before,
            "after": after,
            "comparison": comparison,
            "timestamp": time.time(),
        }
        
        filepath = project_root / "metrics" / filename
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\nResults saved to: {filepath}")


def main():
    """Run before/after test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test KG Query Optimizer before/after")
    parser.add_argument("--workspace-id", default="default", help="Workspace ID")
    parser.add_argument("--before-only", action="store_true", help="Run only before test")
    parser.add_argument("--after-only", action="store_true", help="Run only after test (requires optimizer)")
    
    args = parser.parse_args()
    
    tester = KGOptimizerTester(workspace_id=args.workspace_id)
    
    if args.before_only:
        logger.info("Running BEFORE test only...")
        before_results = tester.test_before()
        tester.save_results(before_results, {}, {}, "kg_optimizer_before_only.json")
        return
    
    if args.after_only:
        logger.info("Running AFTER test only...")
        # Import optimizer (will be created)
        try:
            from core_engine.reasoning.kg_query_optimizer import KGQueryOptimizer
            optimizer = KGQueryOptimizer(
                neo4j_client=tester.neo4j_client,
                openai_client=tester.openai_client,
            )
            after_results = tester.test_after(optimizer)
            tester.save_results({}, after_results, {}, "kg_optimizer_after_only.json")
        except ImportError:
            logger.error("KG Query Optimizer not found. Please implement it first.")
        return
    
    # Run both tests
    logger.info("Running BEFORE test...")
    before_results = tester.test_before()
    
    logger.info("\n" + "=" * 80)
    logger.info("Now implement KG Query Optimizer, then run with --after-only")
    logger.info("=" * 80)
    
    # Save before results
    tester.save_results(before_results, {}, {}, "kg_optimizer_before.json")


if __name__ == "__main__":
    main()
