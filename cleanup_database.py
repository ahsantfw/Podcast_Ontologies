#!/usr/bin/env python3
"""
Cleanup script to delete all data from Neo4j and Qdrant before reprocessing.
Useful for testing accuracy with fresh data.
"""
import os
import sys
from pathlib import Path

# Add repo root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

# Load .env from script directory (ontology_production_v1)
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = SCRIPT_DIR / ".env"

# Load .env file
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=True)
    print(f"📄 Loaded .env from: {ENV_FILE}")
else:
    # Try loading from current directory
    load_dotenv(override=True)
    print(f"⚠️  .env file not found at {ENV_FILE}")
    print(f"   Looking for .env in: {Path.cwd() / '.env'}")
    if not (Path.cwd() / ".env").exists():
        print(f"   ❌ .env file not found! Please create it in {SCRIPT_DIR}")
        print(f"   You can copy from .env.example if it exists")

def get_env(key: str, default: str = None, alt_key: str = None) -> str:
    """Get environment variable, with optional alternative key name."""
    value = os.getenv(key, default)
    if value is None and alt_key:
        value = os.getenv(alt_key, default)
    if value is None:
        env_file_path = ENV_FILE if ENV_FILE.exists() else Path.cwd() / ".env"
        alt_hint = f" or {alt_key}" if alt_key else ""
        raise ValueError(
            f"Environment variable {key}{alt_hint} is not set.\n"
            f"Please check your .env file at: {env_file_path}\n"
            f"Required variables: NEO4J_URI, NEO4J_USER (or NEO4J_USERNAME), NEO4J_PASSWORD"
        )
    return value

def cleanup_neo4j(workspace_id: str = None):
    """Delete all nodes and relationships from Neo4j."""
    
    uri = get_env("NEO4J_URI")
    # Support both NEO4J_USER and NEO4J_USERNAME
    user = get_env("NEO4J_USER", alt_key="NEO4J_USERNAME")
    password = get_env("NEO4J_PASSWORD")
    
    print(f"🔗 Connecting to Neo4j Cloud: {uri}")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # Option 1: Delete everything
            print("🗑️  Deleting ALL nodes and relationships from Neo4j...")
            result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
            deleted = result.single()["deleted"]
            print(f"✅ Deleted {deleted} nodes from Neo4j")
            
            # Option 2: Delete by workspace (commented out - uncomment if you want workspace-specific cleanup)
            # if workspace_id:
            #     print(f"🗑️  Deleting nodes for workspace: {workspace_id}")
            #     result = session.run(
            #         "MATCH (n {workspace_id: $workspace_id}) DETACH DELETE n RETURN count(n) as deleted",
            #         workspace_id=workspace_id
            #     )
            #     deleted = result.single()["deleted"]
            #     print(f"✅ Deleted {deleted} nodes for workspace '{workspace_id}'")
            # else:
            #     print("🗑️  Deleting ALL nodes and relationships from Neo4j...")
            #     result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
            #     deleted = result.single()["deleted"]
            #     print(f"✅ Deleted {deleted} nodes from Neo4j")
            
    except Exception as e:
        print(f"❌ Error cleaning Neo4j: {e}")
        raise
    finally:
        driver.close()

def cleanup_qdrant(collection: str = "ontology_chunks"):
    """Delete all vectors from Qdrant collection."""
    # .env already loaded at module level
    
    qdrant_url = get_env("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = get_env("QDRANT_API_KEY", "")
    
    print(f"🔗 Connecting to Qdrant: {qdrant_url}")
    
    try:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key if qdrant_api_key else None)
        
        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection not in collection_names:
            print(f"⚠️  Collection '{collection}' does not exist. Nothing to delete.")
            return
        
        # Get count before deletion
        info = client.get_collection(collection)
        count_before = info.points_count
        
        if count_before == 0:
            print(f"⚠️  Collection '{collection}' is already empty.")
            return
        
        print(f"🗑️  Deleting {count_before} vectors from Qdrant collection '{collection}'...")
        
        # Option 1: Delete entire collection
        client.delete_collection(collection)
        print(f"✅ Deleted collection '{collection}' ({count_before} vectors)")
        
        # Option 2: Recreate empty collection (for future use)
        # We'll let the pipeline recreate it automatically
        
    except Exception as e:
        print(f"❌ Error cleaning Qdrant: {e}")
        raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup Neo4j and Qdrant databases")
    parser.add_argument("--neo4j-only", action="store_true", help="Only cleanup Neo4j")
    parser.add_argument("--qdrant-only", action="store_true", help="Only cleanup Qdrant")
    parser.add_argument("--workspace-id", default=None, help="Workspace ID to delete (Neo4j only, if not provided deletes all)")
    parser.add_argument("--collection", default="ontology_chunks", help="Qdrant collection name")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("⚠️  WARNING: This will delete ALL data from Neo4j and/or Qdrant!")
        if not args.neo4j_only and not args.qdrant_only:
            print("   - Neo4j: All nodes and relationships")
            print("   - Qdrant: All vectors in collection")
        elif args.neo4j_only:
            print("   - Neo4j: All nodes and relationships")
        elif args.qdrant_only:
            print(f"   - Qdrant: All vectors in '{args.collection}' collection")
        
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Cancelled.")
            return
    
    try:
        if not args.qdrant_only:
            cleanup_neo4j(args.workspace_id)
        
        if not args.neo4j_only:
            cleanup_qdrant(args.collection)
        
        print("\n✅ Cleanup complete! You can now run:")
        print("   python main.py process --input data/transcripts/")
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

