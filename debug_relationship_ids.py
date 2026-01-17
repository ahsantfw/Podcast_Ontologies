#!/usr/bin/env python3
"""Debug script to check if relationship source/target IDs match existing nodes."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.kg.extractor import KGExtractor
from core_engine.chunking import DialogueAwareChunker
from core_engine.ingestion import TranscriptLoader

# Initialize
workspace_id = "default"
client = Neo4jClient(workspace_id=workspace_id)
extractor = KGExtractor(workspace_id=workspace_id)

# Load a sample transcript
loader = TranscriptLoader(workspace_id=workspace_id)
transcripts_dir = project_root / "transcripts"
transcripts = list(transcripts_dir.glob("*.txt"))

if not transcripts:
    print("❌ No transcripts found!")
    sys.exit(1)

print(f"📄 Loading transcript: {transcripts[0].name}")
transcript = loader.load_transcript(transcripts[0])

# Chunk it
chunker = DialogueAwareChunker(workspace_id=workspace_id)
chunks = chunker.chunk_transcript(transcript)
print(f"✅ Created {len(chunks)} chunks")

# Extract from first chunk
print(f"\n🧠 Extracting from first chunk...")
sample_chunk = chunks[0]
extraction = extractor.extract_from_chunks([sample_chunk])

print(f"\n📊 Extraction Results:")
print(f"   Concepts: {len(extraction.get('concepts', []))}")
print(f"   Relationships: {len(extraction.get('relationships', []))}")

# Check what IDs are in relationships
relationships = extraction.get('relationships', [])
if relationships:
    print(f"\n🔍 Checking relationship IDs...")
    for i, rel in enumerate(relationships[:5]):  # Check first 5
        source_id = rel.get('source_id', '')
        target_id = rel.get('target_id', '')
        rel_type = rel.get('type', 'UNKNOWN')
        
        print(f"\n   Relationship {i+1}: {rel_type}")
        print(f"      Source ID: {source_id}")
        print(f"      Target ID: {target_id}")
        
        # Check if source exists
        source_query = """
        MATCH (n)
        WHERE n.id = $id AND n.workspace_id = $workspace_id
        RETURN n.name as name, labels(n) as labels
        LIMIT 1
        """
        source_result = client.execute_read(
            source_query,
            {"id": source_id, "workspace_id": workspace_id}
        )
        
        # Check if target exists
        target_result = client.execute_read(
            source_query,
            {"id": target_id, "workspace_id": workspace_id}
        )
        
        if source_result:
            print(f"      ✅ Source exists: {source_result[0]['name']} ({source_result[0]['labels']})")
        else:
            print(f"      ❌ Source NOT found in database!")
            
        if target_result:
            print(f"      ✅ Target exists: {target_result[0]['name']} ({target_result[0]['labels']})")
        else:
            print(f"      ❌ Target NOT found in database!")

# Check what concept IDs exist in database
print(f"\n📋 Sample concept IDs in database:")
concept_query = """
MATCH (c)
WHERE c.workspace_id = $workspace_id
RETURN c.id as id, c.name as name, labels(c) as labels
LIMIT 10
"""
concepts = client.execute_read(concept_query, {"workspace_id": workspace_id})
for c in concepts:
    print(f"   {c['id']} -> {c['name']} ({c['labels']})")

client.close()

