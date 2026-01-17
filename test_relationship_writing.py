#!/usr/bin/env python3
"""
Test relationship writing to Neo4j.
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
from core_engine.kg.writer import KGWriter
from core_engine.kg.schema import initialize_schema


def test_writing():
    """Test writing relationships."""
    print("=" * 60)
    print("🧪 TESTING RELATIONSHIP WRITING")
    print("=" * 60)
    
    workspace_id = "test_write"
    client = get_neo4j_client(workspace_id=workspace_id)
    writer = KGWriter(client, workspace_id=workspace_id)
    
    try:
        # Initialize schema
        print("\n1️⃣ Initializing schema...")
        initialize_schema(client)
        print("   ✅ Schema initialized")
        
        # First, create some test concepts
        print("\n2️⃣ Creating test concepts...")
        concepts = [
            {
                "id": "meditation",
                "name": "meditation",
                "type": "Practice",
                "description": "A practice",
                "workspace_id": workspace_id,
            },
            {
                "id": "improved_focus",
                "name": "improved focus",
                "type": "Outcome",
                "description": "An outcome",
                "workspace_id": workspace_id,
            },
        ]
        concept_count = writer.write_concepts(concepts)
        print(f"   ✅ Created {concept_count} concepts")
        
        # Verify concepts exist
        query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
        RETURN c.id as id, c.name as name
        """
        result = client.execute_read(query, {"workspace_id": workspace_id})
        print(f"   📊 Concepts in DB: {[r['id'] for r in result]}")
        
        # Now try to write relationships
        print("\n3️⃣ Writing relationships...")
        relationships = [
            {
                "source_id": "meditation",
                "target_id": "improved_focus",
                "type": "CAUSES",
                "description": "Meditation causes improved focus",
                "text_span": "meditation CAUSES improved focus",
                "workspace_id": workspace_id,
                "episode_id": "test",
                "source_path": "test.txt",
                "confidence": 0.9,
            }
        ]
        
        print(f"   Attempting to write {len(relationships)} relationship(s)...")
        print(f"   Source ID: {relationships[0]['source_id']}")
        print(f"   Target ID: {relationships[0]['target_id']}")
        
        # Check if source and target exist
        check_query = """
        MATCH (source {id: $source_id, workspace_id: $workspace_id})
        MATCH (target {id: $target_id, workspace_id: $workspace_id})
        RETURN source.id as source_id, target.id as target_id
        """
        check_result = client.execute_read(
            check_query,
            {
                "source_id": relationships[0]["source_id"],
                "target_id": relationships[0]["target_id"],
                "workspace_id": workspace_id,
            }
        )
        
        if check_result:
            print(f"   ✅ Source and target nodes found: {check_result[0]}")
        else:
            print("   ❌ Source or target nodes NOT found!")
            # Check what nodes exist
            all_nodes = client.execute_read(
                "MATCH (n) WHERE n.workspace_id = $workspace_id RETURN n.id as id, labels(n) as labels",
                {"workspace_id": workspace_id}
            )
            print(f"   Available nodes: {[r['id'] for r in all_nodes]}")
            return
        
        # Try to write
        try:
            rel_count = writer.write_relationships(relationships)
            print(f"   ✅ Wrote {rel_count} relationship(s)")
            
            # Verify relationship was created
            verify_query = """
            MATCH (a)-[r]->(b)
            WHERE r.workspace_id = $workspace_id
            RETURN a.id as source, type(r) as rel_type, b.id as target
            """
            verify_result = client.execute_read(
                verify_query,
                {"workspace_id": workspace_id}
            )
            if verify_result:
                print(f"   ✅ Relationship verified: {verify_result[0]}")
            else:
                print("   ❌ Relationship NOT found in database!")
        except Exception as e:
            print(f"   ❌ Error writing relationships: {e}")
            import traceback
            traceback.print_exc()
        
        # Cleanup
        print("\n4️⃣ Cleaning up...")
        client.execute_write(
            "MATCH (n) WHERE n.workspace_id = $workspace_id DETACH DELETE n",
            {"workspace_id": workspace_id}
        )
        print("   ✅ Cleaned up")
        
    finally:
        client.close()


if __name__ == "__main__":
    test_writing()

