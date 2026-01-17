#!/usr/bin/env python3
"""
Migrate Qdrant embeddings from local to GCP Qdrant.

Usage:
    python migrate_qdrant.py \
        --source http://localhost:6333 \
        --target http://<gcp-qdrant-url>:6333 \
        --collection ontology_chunks
"""

import argparse
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def migrate_collection(
    source_url: str,
    target_url: str,
    collection: str,
    batch_size: int = 100,
    source_api_key: str = None,
    target_api_key: str = None,
):
    """Migrate all points from source Qdrant to target Qdrant."""
    
    print(f"🔗 Connecting to source: {source_url}")
    source_client = QdrantClient(url=source_url, api_key=source_api_key)
    
    print(f"🔗 Connecting to target: {target_url}")
    target_client = QdrantClient(url=target_url, api_key=target_api_key)
    
    # Check source collection exists
    collections = source_client.get_collections().collections
    if not any(c.name == collection for c in collections):
        raise ValueError(f"Collection '{collection}' not found in source Qdrant")
    
    print(f"📊 Reading collection info from source...")
    source_info = source_client.get_collection(collection)
    vector_size = source_info.config.params.vectors.size
    distance = source_info.config.params.vectors.distance
    
    print(f"  - Vector size: {vector_size}")
    print(f"  - Distance: {distance}")
    print(f"  - Points count: {source_info.points_count}")
    
    # Create collection in target (if not exists)
    target_collections = target_client.get_collections().collections
    if not any(c.name == collection for c in target_collections):
        print(f"📝 Creating collection '{collection}' in target...")
        target_client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
    else:
        print(f"⚠️  Collection '{collection}' already exists in target")
        target_info = target_client.get_collection(collection)
        print(f"  - Target has {target_info.points_count} points")
        response = input("Continue migration? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
    
    # Scroll and migrate points in batches
    print(f"🚀 Starting migration (batch size: {batch_size})...")
    
    total_migrated = 0
    offset = None
    
    if HAS_TQDM:
        pbar = tqdm(total=source_info.points_count, unit="points")
    else:
        pbar = None
    
    try:
        while True:
            # Scroll source
            result = source_client.scroll(
                collection_name=collection,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            
            points, next_offset = result
            
            if not points:
                break
            
            # Upsert to target
            target_client.upsert(
                collection_name=collection,
                points=points,
            )
            
            total_migrated += len(points)
            if pbar:
                pbar.update(len(points))
            else:
                print(f"  Migrated {total_migrated}/{source_info.points_count} points...")
            
            if next_offset is None:
                break
            
            offset = next_offset
    finally:
        if pbar:
            pbar.close()
    
    print(f"✅ Migration complete!")
    print(f"   Migrated {total_migrated} points to {target_url}")


def main():
    parser = argparse.ArgumentParser(description="Migrate Qdrant collection")
    parser.add_argument("--source", required=True, help="Source Qdrant URL (e.g., http://localhost:6333)")
    parser.add_argument("--target", required=True, help="Target Qdrant URL (e.g., http://<ip>:6333)")
    parser.add_argument("--collection", default="ontology_chunks", help="Collection name")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for migration")
    parser.add_argument("--source-api-key", default=None, help="Source Qdrant API key (optional)")
    parser.add_argument("--target-api-key", default=None, help="Target Qdrant API key (optional)")
    
    args = parser.parse_args()
    
    try:
        migrate_collection(
            source_url=args.source,
            target_url=args.target,
            collection=args.collection,
            batch_size=args.batch_size,
            source_api_key=args.source_api_key,
            target_api_key=args.target_api_key,
        )
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

