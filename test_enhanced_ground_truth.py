"""
Test Enhanced Ground Truth - Formatting Functions

Tests the enhanced source extraction formatting:
- Episode name formatting
- Timestamp formatting
- Speaker resolution
- Confidence scores
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def test_formatting_functions():
    """Test formatting functions directly."""
    print("=" * 80)
    print("TESTING ENHANCED GROUND TRUTH - FORMATTING FUNCTIONS")
    print("=" * 80)
    
    # Import agent to access methods
    from core_engine.reasoning.agent import PodcastAgent
    
    # Create minimal agent instance (we only need the formatting methods)
    # We'll create a mock or use class methods if possible
    try:
        # Try to create agent with minimal dependencies
        agent = PodcastAgent(
            workspace_id="default",
            hybrid_retriever=None,
            neo4j_client=None,
        )
        
        print("\n✅ Agent initialized successfully!")
        
        # Test episode name formatting
        print("\n" + "=" * 80)
        print("TESTING EPISODE NAME FORMATTING")
        print("=" * 80)
        
        test_episodes = [
            "143_TYLER_COWEN_PART_1",
            "001_PHIL_JACKSON",
            "002_JERROD_CARMICHAEL",
            "022_WHITNEY_CUMMINGS",
            "108_MARLON_BRANDO",
            "unknown",
            "",
        ]
        
        for ep_id in test_episodes:
            formatted = agent._format_episode_name(ep_id)
            print(f"  '{ep_id}' → '{formatted}'")
        
        # Test timestamp formatting
        print("\n" + "=" * 80)
        print("TESTING TIMESTAMP FORMATTING")
        print("=" * 80)
        
        test_timestamps = [
            "00:15:30",
            "01:30:45",
            "00:05:10",
            "15:30",
            "2:45:30",
            "",
            "invalid",
        ]
        
        for ts in test_timestamps:
            formatted = agent._format_timestamp(ts)
            print(f"  '{ts}' → '{formatted}'")
        
        # Test speaker resolution
        print("\n" + "=" * 80)
        print("TESTING SPEAKER RESOLUTION")
        print("=" * 80)
        
        test_cases = [
            ({"speaker": "Tyler Cowen"}, "143_TYLER_COWEN_PART_1"),
            ({"speaker": "Unknown"}, "143_TYLER_COWEN_PART_1"),
            ({"speaker": "Speaker 1"}, "143_TYLER_COWEN_PART_1"),
            ({}, "143_TYLER_COWEN_PART_1"),
            ({"speaker": "Phil Jackson"}, "001_PHIL_JACKSON"),
            ({}, "unknown"),
        ]
        
        for metadata, episode_id in test_cases:
            speaker = agent._resolve_speaker(metadata, episode_id)
            print(f"  Metadata: {metadata}, Episode: {episode_id}")
            print(f"    → Speaker: '{speaker}'")
        
        # Test confidence calculation
        print("\n" + "=" * 80)
        print("TESTING CONFIDENCE CALCULATION")
        print("=" * 80)
        
        test_results = [
            {"score": 0.85, "text": "This is a test"},
            {"score": 0.5, "text": "Another test"},
            {"score": 0.9, "text": "This is a test"},  # Similar text (should boost)
        ]
        
        for i, result in enumerate(test_results):
            confidence = agent._calculate_confidence(result, test_results, source_type="rag")
            print(f"  Result {i+1}: score={result['score']}, text='{result['text'][:30]}...'")
            print(f"    → Confidence: {confidence:.2f}")
        
        print("\n" + "=" * 80)
        print("✅ ALL FORMATTING TESTS COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_formatting_functions()
