#!/usr/bin/env python3
"""
Diagnostic script to check relationship extraction and storage.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add repo root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.logging import get_logger


def get_env(key: str, default: str = None) -> str:
    """Get environment variable."""
    return os.getenv(key, default)


def diagnose_relationships(workspace_id: str = "default"):
    """Diagnose relationship extraction issues."""
    print("=" * 60)
    print("🔍 RELATIONSHIP DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"Workspace: {workspace_id}\n")
    
    client = get_neo4j_client(workspace_id=workspace_id)
    
    try:
        # 1. Check total relationships
        print("1️⃣ Checking Total Relationships...")
        # Relationships don't have workspace_id - filter by connected nodes
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
        RETURN count(r) as total
        """
        result = client.execute_read(query, {"workspace_id": workspace_id})
        total = result[0]["total"] if result else 0
        print(f"   Total relationships: {total}\n")
        
        # 2. Check relationships by type
        print("2️⃣ Checking Relationships by Type...")
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
        RETURN type(r) as rel_type, count(r) as count
        ORDER BY count DESC
        """
        results = client.execute_read(query, {"workspace_id": workspace_id})
        if results:
            for r in results:
                print(f"   {r['rel_type']}: {r['count']}")
        else:
            print("   ❌ No relationships found!")
        print()
        
        # 3. Check if nodes exist (for relationship creation)
        print("3️⃣ Checking Node Counts...")
        query = """
        MATCH (n)
        WHERE n.workspace_id = $workspace_id
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        LIMIT 10
        """
        results = client.execute_read(query, {"workspace_id": workspace_id})
        if results:
            for r in results:
                print(f"   {r['label']}: {r['count']}")
        print()
        
        # 4. Check sample relationships (if any exist)
        if total > 0:
            print("4️⃣ Sample Relationships...")
            query = """
            MATCH (a)-[r]->(b)
            WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
            RETURN a.name as source, type(r) as rel_type, b.name as target, 
                   r.description as description
            LIMIT 10
            """
            results = client.execute_read(query, {"workspace_id": workspace_id})
            for r in results:
                source = r.get('source') or r.get('id', 'Unknown')
                target = r.get('target') or r.get('id', 'Unknown')
                print(f"   {source} --[{r['rel_type']}]--> {target}")
                if r.get('description'):
                    print(f"      Description: {r['description'][:50]}...")
        else:
            print("4️⃣ No relationships to sample\n")
        
        # 5. Check if relationships have workspace_id property
        print("5️⃣ Checking Relationship Properties...")
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
        RETURN 
            count(r) as total,
            count(CASE WHEN r.description IS NOT NULL THEN 1 END) as has_description,
            count(CASE WHEN r.episode_ids IS NOT NULL THEN 1 END) as has_episodes,
            count(CASE WHEN r.source_paths IS NOT NULL THEN 1 END) as has_sources
        LIMIT 1
        """
        result = client.execute_read(query, {"workspace_id": workspace_id})
        if result and result[0]["total"] > 0:
            r = result[0]
            print(f"   Total: {r['total']}")
            print(f"   With description: {r['has_description']}")
            print(f"   With episode_ids: {r['has_episodes']}")
            print(f"   With source_paths: {r['has_sources']}")
        else:
            print("   ❌ No relationships to check properties")
        print()
        
        # 6. Check for nodes that should have relationships
        print("6️⃣ Checking Concepts That Should Have Relationships...")
        query = """
        MATCH (c:Concept)
        WHERE c.workspace_id = $workspace_id
        OPTIONAL MATCH (c)-[r]->(target)
        WHERE target.workspace_id = $workspace_id
        RETURN c.name as concept, count(r) as rel_count
        ORDER BY rel_count DESC
        LIMIT 10
        """
        results = client.execute_read(query, {"workspace_id": workspace_id})
        if results:
            print("   Concepts with most relationships:")
            for r in results:
                print(f"   {r['concept']}: {r['rel_count']} relationships")
        print()
        
        # 7. Check extraction metadata (if stored)
        print("7️⃣ Checking for Relationship Extraction Issues...")
        print("   (This checks if relationships were extracted but not stored)")
        
        # Check if we can find concepts that appear together in same episode
        # (should have relationships)
        query = """
        MATCH (c1:Concept), (c2:Concept)
        WHERE c1.workspace_id = $workspace_id
          AND c2.workspace_id = $workspace_id
          AND c1.id <> c2.id
          AND ANY(ep IN c1.episode_ids WHERE ep IN c2.episode_ids)
        OPTIONAL MATCH (c1)-[r]->(c2)
        WITH c1, c2, count(r) as rel_count
        WHERE rel_count = 0
        RETURN c1.name as source, c2.name as target
        LIMIT 5
        """
        results = client.execute_read(query, {"workspace_id": workspace_id})
        if results:
            print("   ⚠️  Found concepts in same episode without relationships:")
            for r in results:
                print(f"      {r['source']} <-> {r['target']}")
        else:
            print("   ✅ All co-occurring concepts have relationships (or none found)")
        print()
        
        # Summary
        print("=" * 60)
        print("📊 DIAGNOSIS SUMMARY")
        print("=" * 60)
        if total == 0:
            print("❌ CRITICAL: No relationships found in database!")
            print("   Possible causes:")
            print("   1. Relationships not being extracted by LLM")
            print("   2. Relationships extracted but not written to Neo4j")
            print("   3. source_id/target_id mismatch (nodes don't exist)")
            print("   4. workspace_id mismatch")
        elif total < 50:
            print("⚠️  WARNING: Very few relationships found!")
            print(f"   Only {total} relationships for {workspace_id}")
            print("   Expected: 100+ relationships")
        else:
            print(f"✅ Found {total} relationships")
            print("   This is reasonable, but check relationship types above")
        
    finally:
        client.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnose relationship extraction")
    parser.add_argument("--workspace-id", default=None, help="Workspace identifier")
    
    args = parser.parse_args()
    
    workspace_id = args.workspace_id or get_env("WORKSPACE_ID", "default")
    
    diagnose_relationships(workspace_id)

