#!/usr/bin/env python3
"""
Test relationship extraction on a small sample to debug.
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

from langchain_core.documents import Document
from core_engine.kg.extractor import KGExtractor
from core_engine.logging import get_logger


def test_extraction():
    """Test extraction on a small sample."""
    print("=" * 60)
    print("🧪 TESTING RELATIONSHIP EXTRACTION")
    print("=" * 60)
    
    # Create a test chunk with clear relationships
    test_chunk = Document(
        page_content="""
        Phil Jackson emphasizes that meditation CAUSES improved focus. 
        He also says that discipline ENABLES better performance.
        Mindfulness OPTIMIZES clarity and reduces anxiety.
        """,
        metadata={
            "source_path": "test.txt",
            "episode_id": "test_episode",
            "speaker": "Phil Jackson",
            "start_char": 0,
            "end_char": 200,
        }
    )
    
    extractor = KGExtractor(
        model="gpt-4o",  # Use gpt-4o for better extraction
        temperature=0.2,
        batch_size=1,
        confidence_threshold=0.3,  # Lower threshold for testing
        workspace_id="test",
    )
    
    print("\n📝 Test Chunk:")
    print(test_chunk.page_content)
    print()
    
    print("🔍 Extracting...")
    try:
        result = extractor.extract_from_chunks([test_chunk])
        
        print("\n✅ Extraction Results:")
        print(f"   Concepts: {len(result.get('concepts', []))}")
        print(f"   Relationships: {len(result.get('relationships', []))}")
        print(f"   Quotes: {len(result.get('quotes', []))}")
        
        if result.get('relationships'):
            print("\n📊 Relationships Found:")
            for i, rel in enumerate(result['relationships'], 1):
                print(f"\n   {i}. {rel.get('source_id')} --[{rel.get('type')}]--> {rel.get('target_id')}")
                print(f"      Description: {rel.get('description', 'N/A')}")
                print(f"      Confidence: {rel.get('confidence', 'N/A')}")
                print(f"      Text span: {rel.get('text_span', 'N/A')[:100]}")
        else:
            print("\n❌ NO RELATIONSHIPS EXTRACTED!")
            print("   This indicates the LLM is not extracting relationships.")
        
        if result.get('concepts'):
            print("\n📊 Concepts Found:")
            for i, concept in enumerate(result['concepts'][:5], 1):
                print(f"   {i}. {concept.get('name')} (id: {concept.get('id')}, type: {concept.get('type')})")
        
        # Check if source_id/target_id match concept IDs
        if result.get('relationships') and result.get('concepts'):
            print("\n🔗 Checking ID Matching...")
            concept_ids = {c.get('id') for c in result['concepts']}
            for rel in result['relationships']:
                source_id = rel.get('source_id')
                target_id = rel.get('target_id')
                source_match = source_id in concept_ids
                target_match = target_id in concept_ids
                print(f"   {source_id} --[{rel.get('type')}]--> {target_id}")
                print(f"      Source ID exists: {source_match}")
                print(f"      Target ID exists: {target_match}")
                if not source_match or not target_match:
                    print(f"      ⚠️  MISMATCH! Available concept IDs: {list(concept_ids)[:5]}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_extraction()

