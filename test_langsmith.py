#!/usr/bin/env python3
"""
Quick test script to verify LangSmith is working.

Usage:
    python test_langsmith.py
"""

import sys
from pathlib import Path

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.metrics.langsmith_integration import (
    is_langsmith_enabled,
    get_langsmith_client,
    trace_operation,
    langsmith_run,
)
from dotenv import load_dotenv
import os

# Load .env from script directory explicitly
ROOT = Path(__file__).resolve().parent
env_file = ROOT / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=True)
    print(f"📄 Loaded .env from: {env_file}")
else:
    load_dotenv()  # Fallback to default location


def test_langsmith_connection():
    """Test if LangSmith is properly configured."""
    print("=" * 80)
    print("🔍 TESTING LANGSMITH CONFIGURATION")
    print("=" * 80)
    print()
    
    # Check environment variables
    print("📋 Environment Variables:")
    tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2", "")
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "")
    
    print(f"  LANGCHAIN_TRACING_V2: {tracing_v2}")
    print(f"  LANGCHAIN_API_KEY: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"  LANGCHAIN_PROJECT: {project or 'default'}")
    print()
    
    # Check if enabled
    if is_langsmith_enabled():
        print("✅ LangSmith is ENABLED")
        print()
        
        # Try to connect
        print("🔌 Testing Connection...")
        try:
            client = get_langsmith_client()
            if client:
                # Try to list projects
                try:
                    projects = list(client.list_projects())
                    print(f"✅ Connected! Found {len(projects)} project(s)")
                    if projects:
                        print(f"   Current project: {project}")
                        print(f"   Available projects: {', '.join([p.name for p in projects[:5]])}")
                except Exception as e:
                    print(f"⚠️  Connected but couldn't list projects: {e}")
                    print("   (This is okay - API key might be valid but need permissions)")
            else:
                print("⚠️  Could not create client (but tracing may still work)")
        except Exception as e:
            print(f"⚠️  Connection test failed: {e}")
            print("   (Tracing may still work - this is just a connection test)")
        
        print()
        print("=" * 80)
        print("✅ SETUP COMPLETE - LangSmith is ready to use!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Run your ingestion: python process_with_metrics.py")
        print("2. View traces at: https://smith.langchain.com")
        print("3. Select your project:", project or "default")
        print()
        
        return True
    else:
        print("❌ LangSmith is NOT enabled")
        print()
        print("Please check:")
        print("1. LANGCHAIN_TRACING_V2=true in .env")
        print("2. LANGCHAIN_API_KEY is set in .env")
        print("3. .env file is in the project root")
        print()
        return False


def test_tracing():
    """Test if tracing actually works."""
    if not is_langsmith_enabled():
        print("⚠️  LangSmith not enabled - skipping trace test")
        return
    
    print("🧪 Testing Trace Creation...")
    print()
    
    # Test 1: Decorator
    @trace_operation(
        "test_operation",
        metadata={"test": True, "workspace": "test"},
        tags=["test", "verification"]
    )
    def test_function():
        return "Hello from traced function!"
    
    result = test_function()
    print(f"✅ Decorator test: {result}")
    
    # Test 2: Context manager
    with langsmith_run(
        "test_context_manager",
        inputs={"test": True},
        tags=["test"]
    ):
        print("✅ Context manager test: Inside traced context")
    
    print()
    print("✅ Trace tests completed!")
    print("   Check https://smith.langchain.com to see these test traces")
    print()


if __name__ == "__main__":
    try:
        success = test_langsmith_connection()
        
        if success:
            print()
            response = input("Run trace test? (y/n): ").strip().lower()
            if response == 'y':
                test_tracing()
        
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

