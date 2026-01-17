#!/usr/bin/env python3
"""
Test Knowledge Graph accuracy with client's actual questions.
Verifies that the KG has all required concepts, relationships, and can answer client questions.
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

# Add repo root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

from core_engine.reasoning import create_reasoner
from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.logging import get_logger


def get_env(key: str, default: str = None) -> str:
    """Get environment variable."""
    return os.getenv(key, default)


class KGAccuracyTester:
    """Test KG accuracy with client questions."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.reasoner = create_reasoner(
            workspace_id=workspace_id,
            use_llm=True,
            use_hybrid=True,
        )
        self.client = get_neo4j_client(workspace_id=workspace_id)
        self.logger = get_logger("kg_accuracy_test", workspace_id=workspace_id)
        self.results = []
    
    def test_kg_stats(self) -> Dict[str, Any]:
        """Test basic KG statistics."""
        print("\n" + "=" * 60)
        print("📊 Testing Knowledge Graph Statistics")
        print("=" * 60)
        
        stats = {}
        
        # Count nodes by type
        node_types = [
            "Concept", "Practice", "CognitiveState", "BehavioralPattern",
            "Principle", "Outcome", "Causality", "Person", "Quote"
        ]
        
        for node_type in node_types:
            query = f"""
            MATCH (n:{node_type})
            WHERE n.workspace_id = $workspace_id
            RETURN count(n) as count
            """
            result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
            count = result[0]["count"] if result else 0
            stats[node_type] = count
            print(f"  {node_type}: {count}")
        
        # Count relationships
        rel_types = [
            "CAUSES", "INFLUENCES", "OPTIMIZES", "ENABLES",
            "REDUCES", "LEADS_TO", "REQUIRES", "RELATES_TO", "CROSS_EPISODE"
        ]
        
        print("\n  Relationships:")
        for rel_type in rel_types:
            query = f"""
            MATCH (a)-[r:{rel_type}]->(b)
            WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
            RETURN count(r) as count
            """
            result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
            count = result[0]["count"] if result else 0
            stats[f"{rel_type}_count"] = count
            print(f"    {rel_type}: {count}")
        
        # Count quotes
        query = """
        MATCH (q:Quote)
        WHERE q.workspace_id = $workspace_id
        RETURN count(q) as count
        """
        result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
        stats["quotes"] = result[0]["count"] if result else 0
        print(f"\n  Quotes: {stats['quotes']}")
        
        # Count cross-episode concepts
        query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND c.episode_ids IS NOT NULL
          AND size(c.episode_ids) >= 2
        RETURN count(c) as count
        """
        result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
        stats["cross_episode_concepts"] = result[0]["count"] if result else 0
        print(f"  Cross-episode concepts: {stats['cross_episode_concepts']}")
        
        return stats
    
    def test_client_question(self, question: str, expected_elements: List[str] = None) -> Dict[str, Any]:
        """
        Test a client question and verify answer quality.
        
        Args:
            question: Question to test
            expected_elements: List of expected elements in answer (e.g., ["practices", "clarity"])
        
        Returns:
            Test result dictionary
        """
        print("\n" + "=" * 60)
        print(f"❓ Question: {question}")
        print("=" * 60)
        
        try:
            result = self.reasoner.query(question)
            answer = result.get("answer", "")
            metadata = result.get("metadata", {})
            
            print(f"\n💡 Answer:")
            print("-" * 60)
            print(answer[:500] + "..." if len(answer) > 500 else answer)
            print("-" * 60)
            
            # Check answer quality
            quality_checks = {
                "has_answer": len(answer) > 50,
                "mentions_sources": "episode" in answer.lower() or "source" in answer.lower(),
                "has_structure": len(answer.split("\n")) > 1 or len(answer.split(".")) > 2,
                "method": metadata.get("method", "unknown"),
                "kg_results": metadata.get("kg_count", 0),
                "rag_results": metadata.get("rag_count", 0),
            }
            
            # Check for expected elements
            if expected_elements:
                for element in expected_elements:
                    quality_checks[f"mentions_{element}"] = element.lower() in answer.lower()
            
            print(f"\n📊 Quality Checks:")
            for check, passed in quality_checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}: {passed}")
            
            # Verify KG has relevant data
            kg_verification = self._verify_kg_data(question)
            quality_checks.update(kg_verification)
            
            test_result = {
                "question": question,
                "answer": answer,
                "quality_checks": quality_checks,
                "metadata": metadata,
                "passed": all(v for k, v in quality_checks.items() if isinstance(v, bool) and k.startswith("has_") or k.startswith("mentions_")),
            }
            
            self.results.append(test_result)
            return test_result
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            test_result = {
                "question": question,
                "error": str(e),
                "passed": False,
            }
            self.results.append(test_result)
            return test_result
    
    def _verify_kg_data(self, question: str) -> Dict[str, Any]:
        """Verify KG has relevant data for the question."""
        verification = {}
        
        # Extract keywords from question
        import re
        stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why", "does", "do", "should", "can", "will"}
        keywords = [w.lower() for w in re.findall(r'\b\w+\b', question) if w.lower() not in stop_words and len(w) > 2]
        
        if not keywords:
            return verification
        
        # Check if concepts exist for keywords
        for keyword in keywords[:3]:  # Check first 3 keywords
            query = """
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND (toLower(c.name) CONTAINS $keyword OR toLower(c.description) CONTAINS $keyword)
            RETURN count(c) as count
            """
            result = self.client.execute_read(query, {"workspace_id": self.workspace_id, "keyword": keyword})
            count = result[0]["count"] if result else 0
            verification[f"kg_has_{keyword}"] = count > 0
        
        return verification
    
    def test_relationship_queries(self) -> None:
        """Test relationship-specific queries."""
        print("\n" + "=" * 60)
        print("🔗 Testing Relationship Queries")
        print("=" * 60)
        
        # Test OPTIMIZES relationships
        query = """
        MATCH (p:Practice)-[r:OPTIMIZES]->(o:Outcome)
        WHERE p.workspace_id = $workspace_id AND o.workspace_id = $workspace_id
        RETURN p.name as practice, o.name as outcome, count(r) as count
        ORDER BY count DESC
        LIMIT 10
        """
        result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
        print(f"\n  OPTIMIZES relationships: {len(result)}")
        if result:
            print("  Examples:")
            for r in result[:3]:
                print(f"    - {r['practice']} → OPTIMIZES → {r['outcome']}")
        
        # Test CAUSES relationships
        query = """
        MATCH (c1)-[r:CAUSES]->(c2)
        WHERE c1.workspace_id = $workspace_id AND c2.workspace_id = $workspace_id
        RETURN count(r) as count
        """
        result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
        count = result[0]["count"] if result else 0
        print(f"\n  CAUSES relationships: {count}")
        
        # Test CROSS_EPISODE relationships (if they exist)
        query = """
        MATCH (c1)-[r:CROSS_EPISODE]->(c2)
        WHERE c1.workspace_id = $workspace_id AND c2.workspace_id = $workspace_id
        RETURN count(r) as count
        """
        try:
            result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
            count = result[0]["count"] if result else 0
            print(f"  CROSS_EPISODE relationships: {count}")
        except:
            print(f"  CROSS_EPISODE relationships: 0 (type not in database)")
    
    def test_provenance(self) -> None:
        """Test that nodes have proper provenance (source, timestamp, etc.)."""
        print("\n" + "=" * 60)
        print("📋 Testing Provenance (Source Tracking)")
        print("=" * 60)
        
        # Check concepts have source paths
        query = """
        MATCH (c:Concept)
        WHERE c.workspace_id = $workspace_id
        RETURN 
          count(c) as total,
          count(CASE WHEN c.source_paths IS NOT NULL THEN 1 END) as has_sources,
          count(CASE WHEN c.episode_ids IS NOT NULL THEN 1 END) as has_episodes,
          count(CASE WHEN c.timestamps IS NOT NULL THEN 1 END) as has_timestamps
        """
        result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
        if result:
            r = result[0]
            print(f"\n  Concepts:")
            print(f"    Total: {r['total']}")
            print(f"    With source paths: {r['has_sources']} ({r['has_sources']/r['total']*100:.1f}%)")
            print(f"    With episode IDs: {r['has_episodes']} ({r['has_episodes']/r['total']*100:.1f}%)")
            print(f"    With timestamps: {r['has_timestamps']} ({r['has_timestamps']/r['total']*100:.1f}%)")
        
        # Check quotes have provenance
        query = """
        MATCH (q:Quote)
        WHERE q.workspace_id = $workspace_id
        RETURN 
          count(q) as total,
          count(CASE WHEN q.source_path IS NOT NULL THEN 1 END) as has_source,
          count(CASE WHEN q.episode_id IS NOT NULL THEN 1 END) as has_episode,
          count(CASE WHEN q.timestamp IS NOT NULL THEN 1 END) as has_timestamp,
          count(CASE WHEN q.speaker IS NOT NULL THEN 1 END) as has_speaker
        """
        result = self.client.execute_read(query, {"workspace_id": self.workspace_id})
        if result:
            r = result[0]
            print(f"\n  Quotes:")
            print(f"    Total: {r['total']}")
            print(f"    With source: {r['has_source']} ({r['has_source']/r['total']*100:.1f}%)")
            print(f"    With episode: {r['has_episode']} ({r['has_episode']/r['total']*100:.1f}%)")
            print(f"    With timestamp: {r['has_timestamp']} ({r['has_timestamp']/r['total']*100:.1f}%)")
            print(f"    With speaker: {r['has_speaker']} ({r['has_speaker']/r['total']*100:.1f}%)")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all accuracy tests."""
        print("\n" + "=" * 60)
        print("🧪 KNOWLEDGE GRAPH ACCURACY TEST SUITE")
        print("=" * 60)
        print(f"Workspace: {self.workspace_id}")
        
        # Test 1: Basic statistics
        stats = self.test_kg_stats()
        
        # Test 2: Provenance
        self.test_provenance()
        
        # Test 3: Relationships
        self.test_relationship_queries()
        
        # Test 4: Client's actual questions
        print("\n" + "=" * 60)
        print("❓ Testing Client Questions")
        print("=" * 60)
        
        client_questions = [
            # From requirements document
            {
                "question": "Across this entire corpus, what practices are most associated with improving clarity?",
                "expected": ["practices", "clarity", "improving"]
            },
            {
                "question": "How does reflection relate to decision-making quality?",
                "expected": ["reflection", "decision-making", "quality"]
            },
            {
                "question": "What are the core ideas that recur most frequently about creativity?",
                "expected": ["creativity", "ideas", "recur"]
            },
            {
                "question": "What did Phil Jackson consistently emphasize about discipline across different talks?",
                "expected": ["Phil Jackson", "discipline", "emphasize"]
            },
            {
                "question": "If someone wants to reduce anxiety, what concepts or practices does this knowledge base suggest and why?",
                "expected": ["anxiety", "practices", "reduce"]
            },
            # Original intention questions
            {
                "question": "What should I do with my life?",
                "expected": ["life", "advice", "guidance"]
            },
            {
                "question": "How do I overcome obstacles?",
                "expected": ["obstacles", "overcome", "practices"]
            },
            {
                "question": "What makes good art?",
                "expected": ["art", "good", "creativity"]
            },
            {
                "question": "What practices does Phil Jackson recommend?",
                "expected": ["Phil Jackson", "practices", "recommend"]
            },
            {
                "question": "What concepts appear in multiple episodes?",
                "expected": ["concepts", "episodes", "multiple"]
            },
        ]
        
        for i, test_case in enumerate(client_questions, 1):
            print(f"\n[Test {i}/{len(client_questions)}]")
            self.test_client_question(
                test_case["question"],
                test_case.get("expected", [])
            )
        
        # Summary
        self.print_summary()
        
        return {
            "stats": stats,
            "test_results": self.results,
        }
    
    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("passed", False))
        failed = total - passed
        
        print(f"\n  Total Questions Tested: {total}")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  Success Rate: {passed/total*100:.1f}%")
        
        if failed > 0:
            print(f"\n  Failed Questions:")
            for r in self.results:
                if not r.get("passed", False):
                    print(f"    - {r['question']}")
                    if "error" in r:
                        print(f"      Error: {r['error']}")
        
        print("\n" + "=" * 60)
    
    def close(self):
        """Clean up resources."""
        self.reasoner.close()
        self.client.close()


def main():
    """Run KG accuracy tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Knowledge Graph accuracy with client questions")
    parser.add_argument("--workspace-id", default=None, help="Workspace identifier")
    parser.add_argument("--question", help="Test a single question")
    
    args = parser.parse_args()
    
    workspace_id = args.workspace_id or get_env("WORKSPACE_ID", "default")
    
    tester = KGAccuracyTester(workspace_id=workspace_id)
    
    try:
        if args.question:
            # Test single question
            tester.test_client_question(args.question)
        else:
            # Run full test suite
            tester.run_all_tests()
    finally:
        tester.close()


if __name__ == "__main__":
    main()

