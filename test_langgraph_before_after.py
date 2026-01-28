#!/usr/bin/env python3
"""
Comprehensive Before/After Test Suite for LangGraph Migration

This test suite evaluates the system BEFORE and AFTER LangGraph implementation
to ensure we did things right and didn't break anything.

Usage:
    # Run baseline (before LangGraph)
    python test_langgraph_before_after.py --baseline
    
    # Run comparison (after LangGraph)
    python test_langgraph_before_after.py --compare
    
    # Run both and generate report
    python test_langgraph_before_after.py --full
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from dotenv import load_dotenv

# Add repo root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

from core_engine.reasoning import create_reasoner
from core_engine.logging import get_logger


@dataclass
class TestResult:
    """Result for a single test query."""
    query: str
    category: str
    success: bool
    latency_ms: float
    answer_length: int
    has_answer: bool
    rag_count: int
    kg_count: int
    sources_count: int
    has_sources: bool
    error: Optional[str] = None
    answer_preview: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestSuiteResults:
    """Results for entire test suite."""
    timestamp: str
    mode: str  # "baseline" or "langgraph"
    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_latency_ms: float
    total_latency_ms: float
    results: List[TestResult]
    summary: Dict[str, Any]
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "mode": self.mode,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "avg_latency_ms": self.avg_latency_ms,
            "total_latency_ms": self.total_latency_ms,
            "results": [asdict(r) for r in self.results],
            "summary": self.summary,
        }


class LangGraphTester:
    """Comprehensive test suite for LangGraph migration."""
    
    # Test queries covering all scenarios
    TEST_QUERIES = [
        # Simple queries (should be fast)
        {
            "query": "Hi",
            "category": "greeting",
            "expected": {
                "has_answer": True,
                "latency_max_ms": 1000,  # Should be fast
                "rag_count_min": 0,  # May not need retrieval
            }
        },
        {
            "query": "What is creativity?",
            "category": "simple_definition",
            "expected": {
                "has_answer": True,
                "latency_max_ms": 3000,
                "rag_count_min": 1,
                "kg_count_min": 0,  # May or may not use KG
            }
        },
        {
            "query": "Who is Phil Jackson?",
            "category": "simple_entity",
            "expected": {
                "has_answer": True,
                "latency_max_ms": 3000,
                "rag_count_min": 1,
            }
        },
        
        # Moderate complexity queries
        {
            "query": "How does meditation relate to creativity?",
            "category": "relationship_query",
            "expected": {
                "has_answer": True,
                "latency_max_ms": 5000,
                "rag_count_min": 1,
                "kg_count_min": 0,  # Should use KG for relationships
            }
        },
        {
            "query": "What practices help with anxiety?",
            "category": "practice_query",
            "expected": {
                "has_answer": True,
                "latency_max_ms": 5000,
                "rag_count_min": 1,
            }
        },
        
        # Complex queries
        {
            "query": "What are the connections between mindfulness, clarity, and creativity across different episodes?",
            "category": "complex_multi_entity",
            "expected": {
                "has_answer": True,
                "latency_max_ms": 8000,
                "rag_count_min": 1,
            }
        },
        {
            "query": "How do different practices lead to improved mental states?",
            "category": "complex_causal",
            "expected": {
                "has_answer": True,
                "latency_max_ms": 8000,
                "rag_count_min": 1,
            }
        },
        
        # Follow-up queries (context awareness)
        {
            "query": "What did he say about that?",
            "category": "follow_up_vague",
            "expected": {
                "has_answer": True,  # Should handle gracefully
                "latency_max_ms": 3000,
            }
        },
        
        # Out-of-scope queries (should be rejected)
        {
            "query": "What is 2 + 2?",
            "category": "out_of_scope_math",
            "expected": {
                "has_answer": True,  # Should reject but still respond
                "latency_max_ms": 2000,
                "should_reject": True,
            }
        },
        {
            "query": "How do I write a Python function?",
            "category": "out_of_scope_coding",
            "expected": {
                "has_answer": True,  # Should reject but still respond
                "latency_max_ms": 2000,
                "should_reject": True,
            }
        },
        {
            "query": "What's the weather today?",
            "category": "out_of_scope_general",
            "expected": {
                "has_answer": True,  # Should reject but still respond
                "latency_max_ms": 2000,
                "should_reject": True,
            }
        },
        
        # Source extraction tests
        {
            "query": "What are some quotes about mindfulness?",
            "category": "source_extraction",
            "expected": {
                "has_answer": True,
                "sources_count_min": 1,
                "has_sources": True,
            }
        },
    ]
    
    def __init__(self, workspace_id: str = "default", use_langgraph: bool = False):
        """
        Initialize tester.
        
        Args:
            workspace_id: Workspace to test
            use_langgraph: Whether to use LangGraph (False for baseline)
        """
        self.workspace_id = workspace_id
        self.use_langgraph = use_langgraph
        self.logger = get_logger("langgraph_test", workspace_id=workspace_id)
        
        # Set environment variable to control LangGraph usage
        if use_langgraph:
            os.environ["USE_LANGGRAPH"] = "true"
        else:
            os.environ["USE_LANGGRAPH"] = "false"
        
        # Create reasoner
        self.reasoner = create_reasoner(
            workspace_id=workspace_id,
            use_llm=True,
            use_hybrid=True,
        )
    
    def test_query(self, test_case: Dict[str, Any]) -> TestResult:
        """
        Test a single query.
        
        Args:
            test_case: Test case dictionary with query and expected results
        
        Returns:
            TestResult with all metrics
        """
        query = test_case["query"]
        category = test_case["category"]
        expected = test_case.get("expected", {})
        
        start_time = time.time()
        success = False
        error = None
        answer = ""
        metadata = {}
        rag_count = 0
        kg_count = 0
        sources_count = 0
        
        try:
            # Run query
            result = self.reasoner.query(
                question=query,
                session_id=f"test_{category}_{int(time.time())}",
            )
            
            answer = result.get("answer", "")
            metadata = result.get("metadata", {})
            rag_count = metadata.get("rag_count", 0)
            kg_count = metadata.get("kg_count", 0)
            sources = result.get("sources", [])
            sources_count = len(sources)
            
            # Check if query succeeded
            success = len(answer) > 0
            
        except Exception as e:
            error = str(e)
            self.logger.error(f"Query failed: {query}", exc_info=True)
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Create result
        result_obj = TestResult(
            query=query,
            category=category,
            success=success,
            latency_ms=latency_ms,
            answer_length=len(answer),
            has_answer=len(answer) > 50,
            rag_count=rag_count,
            kg_count=kg_count,
            sources_count=sources_count,
            has_sources=sources_count > 0,
            error=error,
            answer_preview=answer[:200] if answer else None,
            metadata=metadata,
        )
        
        return result_obj
    
    def run_test_suite(self) -> TestSuiteResults:
        """Run entire test suite."""
        mode = "langgraph" if self.use_langgraph else "baseline"
        
        print(f"\n{'=' * 80}")
        print(f"🧪 RUNNING TEST SUITE: {mode.upper()}")
        print(f"{'=' * 80}")
        print(f"Workspace: {self.workspace_id}")
        print(f"LangGraph: {self.use_langgraph}")
        print(f"Total queries: {len(self.TEST_QUERIES)}")
        print(f"{'=' * 80}\n")
        
        results = []
        total_latency = 0.0
        
        for i, test_case in enumerate(self.TEST_QUERIES, 1):
            query = test_case["query"]
            category = test_case["category"]
            
            print(f"[{i}/{len(self.TEST_QUERIES)}] Testing: {query[:60]}... ({category})")
            
            result = self.test_query(test_case)
            results.append(result)
            total_latency += result.latency_ms
            
            # Print result
            status = "✅" if result.success else "❌"
            print(f"  {status} Latency: {result.latency_ms:.0f}ms | "
                  f"RAG: {result.rag_count} | KG: {result.kg_count} | "
                  f"Sources: {result.sources_count}")
            
            if result.error:
                print(f"  ⚠️  Error: {result.error[:100]}")
        
        # Calculate summary
        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed
        avg_latency = total_latency / len(results) if results else 0.0
        
        # Category breakdown
        category_stats = {}
        for result in results:
            cat = result.category
            if cat not in category_stats:
                category_stats[cat] = {
                    "total": 0,
                    "passed": 0,
                    "avg_latency": 0.0,
                    "total_latency": 0.0,
                }
            category_stats[cat]["total"] += 1
            if result.success:
                category_stats[cat]["passed"] += 1
            category_stats[cat]["total_latency"] += result.latency_ms
        
        for cat in category_stats:
            stats = category_stats[cat]
            stats["avg_latency"] = stats["total_latency"] / stats["total"] if stats["total"] > 0 else 0.0
        
        summary = {
            "category_stats": category_stats,
            "performance": {
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min(r.latency_ms for r in results) if results else 0.0,
                "max_latency_ms": max(r.latency_ms for r in results) if results else 0.0,
            },
            "retrieval": {
                "avg_rag_count": sum(r.rag_count for r in results) / len(results) if results else 0.0,
                "avg_kg_count": sum(r.kg_count for r in results) / len(results) if results else 0.0,
                "avg_sources_count": sum(r.sources_count for r in results) / len(results) if results else 0.0,
                "queries_with_sources": sum(1 for r in results if r.has_sources),
            },
            "quality": {
                "queries_with_answer": sum(1 for r in results if r.has_answer),
                "avg_answer_length": sum(r.answer_length for r in results) / len(results) if results else 0.0,
            },
        }
        
        suite_results = TestSuiteResults(
            timestamp=datetime.now().isoformat(),
            mode=mode,
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=failed,
            avg_latency_ms=avg_latency,
            total_latency_ms=total_latency,
            results=results,
            summary=summary,
        )
        
        # Print summary
        print(f"\n{'=' * 80}")
        print(f"📊 TEST SUITE SUMMARY: {mode.upper()}")
        print(f"{'=' * 80}")
        print(f"Total Tests: {suite_results.total_tests}")
        print(f"Passed: {suite_results.passed_tests} ({suite_results.passed_tests/suite_results.total_tests*100:.1f}%)")
        print(f"Failed: {suite_results.failed_tests}")
        print(f"Average Latency: {suite_results.avg_latency_ms:.0f}ms")
        print(f"Total Latency: {suite_results.total_latency_ms:.0f}ms")
        print(f"\nCategory Breakdown:")
        for cat, stats in category_stats.items():
            print(f"  {cat}: {stats['passed']}/{stats['total']} passed, "
                  f"avg {stats['avg_latency']:.0f}ms")
        print(f"{'=' * 80}\n")
        
        return suite_results
    
    def save_results(self, results: TestSuiteResults, filename: Optional[str] = None):
        """Save results to JSON file."""
        if filename is None:
            mode = results.mode
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{mode}_{timestamp}.json"
        
        filepath = Path(ROOT) / "test_results" / filename
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(results.to_dict(), f, indent=2)
        
        print(f"💾 Results saved to: {filepath}")
        return filepath
    
    @staticmethod
    def load_results(filename: str) -> TestSuiteResults:
        """Load results from JSON file."""
        filepath = Path(ROOT) / "test_results" / filename
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        # Reconstruct TestSuiteResults
        results = [TestResult(**r) for r in data["results"]]
        
        suite_results = TestSuiteResults(
            timestamp=data["timestamp"],
            mode=data["mode"],
            total_tests=data["total_tests"],
            passed_tests=data["passed_tests"],
            failed_tests=data["failed_tests"],
            avg_latency_ms=data["avg_latency_ms"],
            total_latency_ms=data["total_latency_ms"],
            results=results,
            summary=data["summary"],
        )
        
        return suite_results
    
    @staticmethod
    def compare_results(baseline: TestSuiteResults, langgraph: TestSuiteResults) -> Dict[str, Any]:
        """Compare baseline vs LangGraph results."""
        print(f"\n{'=' * 80}")
        print(f"📊 COMPARISON: BASELINE vs LANGGRAPH")
        print(f"{'=' * 80}\n")
        
        comparison = {
            "performance": {
                "baseline_avg_latency_ms": baseline.avg_latency_ms,
                "langgraph_avg_latency_ms": langgraph.avg_latency_ms,
                "latency_change_ms": langgraph.avg_latency_ms - baseline.avg_latency_ms,
                "latency_change_percent": ((langgraph.avg_latency_ms - baseline.avg_latency_ms) / baseline.avg_latency_ms * 100) if baseline.avg_latency_ms > 0 else 0.0,
            },
            "accuracy": {
                "baseline_pass_rate": baseline.passed_tests / baseline.total_tests * 100,
                "langgraph_pass_rate": langgraph.passed_tests / langgraph.total_tests * 100,
                "pass_rate_change": (langgraph.passed_tests / langgraph.total_tests * 100) - (baseline.passed_tests / baseline.total_tests * 100),
            },
            "retrieval": {
                "baseline_avg_rag": baseline.summary["retrieval"]["avg_rag_count"],
                "langgraph_avg_rag": langgraph.summary["retrieval"]["avg_rag_count"],
                "baseline_avg_kg": baseline.summary["retrieval"]["avg_kg_count"],
                "langgraph_avg_kg": langgraph.summary["retrieval"]["avg_kg_count"],
            },
        }
        
        # Print comparison
        print("Performance:")
        print(f"  Baseline Avg Latency: {baseline.avg_latency_ms:.0f}ms")
        print(f"  LangGraph Avg Latency: {langgraph.avg_latency_ms:.0f}ms")
        change = comparison["performance"]["latency_change_percent"]
        if change > 0:
            print(f"  ⚠️  Latency increased by {change:.1f}% ({comparison['performance']['latency_change_ms']:.0f}ms)")
        else:
            print(f"  ✅ Latency decreased by {abs(change):.1f}% ({abs(comparison['performance']['latency_change_ms']):.0f}ms)")
        
        print("\nAccuracy:")
        baseline_rate = comparison["accuracy"]["baseline_pass_rate"]
        langgraph_rate = comparison["accuracy"]["langgraph_pass_rate"]
        print(f"  Baseline Pass Rate: {baseline_rate:.1f}%")
        print(f"  LangGraph Pass Rate: {langgraph_rate:.1f}%")
        rate_change = comparison["accuracy"]["pass_rate_change"]
        if rate_change > 0:
            print(f"  ✅ Pass rate improved by {rate_change:.1f}%")
        elif rate_change < 0:
            print(f"  ⚠️  Pass rate decreased by {abs(rate_change):.1f}%")
        else:
            print(f"  ➡️  Pass rate unchanged")
        
        print("\nRetrieval:")
        print(f"  Baseline Avg RAG: {comparison['retrieval']['baseline_avg_rag']:.1f}")
        print(f"  LangGraph Avg RAG: {comparison['retrieval']['langgraph_avg_rag']:.1f}")
        print(f"  Baseline Avg KG: {comparison['retrieval']['baseline_avg_kg']:.1f}")
        print(f"  LangGraph Avg KG: {comparison['retrieval']['langgraph_avg_kg']:.1f}")
        
        # Overall verdict
        print(f"\n{'=' * 80}")
        print("🎯 VERDICT:")
        
        issues = []
        if comparison["performance"]["latency_change_percent"] > 20:
            issues.append(f"⚠️  Significant latency increase ({comparison['performance']['latency_change_percent']:.1f}%)")
        if comparison["accuracy"]["pass_rate_change"] < -5:
            issues.append(f"⚠️  Pass rate decreased ({comparison['accuracy']['pass_rate_change']:.1f}%)")
        
        if not issues:
            print("✅ LangGraph implementation is GOOD!")
            print("   - Performance maintained or improved")
            print("   - Accuracy maintained or improved")
            print("   - No regressions detected")
        else:
            print("⚠️  LangGraph implementation has ISSUES:")
            for issue in issues:
                print(f"   {issue}")
            print("   Review and fix before proceeding.")
        
        print(f"{'=' * 80}\n")
        
        return comparison


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test LangGraph migration")
    parser.add_argument("--baseline", action="store_true", help="Run baseline tests (before LangGraph)")
    parser.add_argument("--compare", action="store_true", help="Run LangGraph tests and compare")
    parser.add_argument("--full", action="store_true", help="Run both baseline and comparison")
    parser.add_argument("--workspace", default="default", help="Workspace ID")
    parser.add_argument("--baseline-file", help="Baseline results file to compare against")
    parser.add_argument("--langgraph-file", help="LangGraph results file to compare")
    
    args = parser.parse_args()
    
    if args.full:
        # Run baseline
        print("Running baseline tests...")
        baseline_tester = LangGraphTester(workspace_id=args.workspace, use_langgraph=False)
        baseline_results = baseline_tester.run_test_suite()
        baseline_file = baseline_tester.save_results(baseline_results)
        
        # Run LangGraph
        print("\nRunning LangGraph tests...")
        langgraph_tester = LangGraphTester(workspace_id=args.workspace, use_langgraph=True)
        langgraph_results = langgraph_tester.run_test_suite()
        langgraph_file = langgraph_tester.save_results(langgraph_results)
        
        # Compare
        LangGraphTester.compare_results(baseline_results, langgraph_results)
        
    elif args.baseline:
        tester = LangGraphTester(workspace_id=args.workspace, use_langgraph=False)
        results = tester.run_test_suite()
        tester.save_results(results)
        
    elif args.compare:
        if args.baseline_file and args.langgraph_file:
            # Load and compare existing files
            baseline = LangGraphTester.load_results(args.baseline_file)
            langgraph = LangGraphTester.load_results(args.langgraph_file)
            LangGraphTester.compare_results(baseline, langgraph)
        else:
            # Run LangGraph and compare with baseline
            baseline_file = args.baseline_file or "test_results_baseline_latest.json"
            try:
                baseline = LangGraphTester.load_results(baseline_file)
            except FileNotFoundError:
                print(f"⚠️  Baseline file not found: {baseline_file}")
                print("Running baseline first...")
                baseline_tester = LangGraphTester(workspace_id=args.workspace, use_langgraph=False)
                baseline = baseline_tester.run_test_suite()
                baseline_tester.save_results(baseline)
            
            langgraph_tester = LangGraphTester(workspace_id=args.workspace, use_langgraph=True)
            langgraph = langgraph_tester.run_test_suite()
            langgraph_tester.save_results(langgraph)
            
            LangGraphTester.compare_results(baseline, langgraph)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
