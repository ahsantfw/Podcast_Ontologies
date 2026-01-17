#!/usr/bin/env python3
"""
Validate .env file - check if all required environment variables are set.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Required variables (with alternative names)
REQUIRED_VARS = {
    "NEO4J_URI": ("Neo4j Cloud connection URI (e.g., neo4j+s://xxx.databases.neo4j.io)", None),
    "NEO4J_USER": ("Neo4j username (usually 'neo4j')", "NEO4J_USERNAME"),  # Support both
    "NEO4J_PASSWORD": ("Neo4j Cloud password", None),
    "OPENAI_API_KEY": ("OpenAI API key for LLM extraction", None),
}

OPTIONAL_VARS = {
    "QDRANT_URL": "Qdrant URL (default: http://localhost:6333)",
    "QDRANT_API_KEY": "Qdrant API key (optional for local)",
    "WORKSPACE_ID": "Workspace identifier (default: 'default')",
}

def main():
    # Load .env from script directory
    script_dir = Path(__file__).resolve().parent
    env_file = script_dir / ".env"
    
    if not env_file.exists():
        print(f"❌ .env file not found at: {env_file}")
        print(f"\n📝 Create .env file with the following variables:")
        print("\n# Required:")
        for var, desc in REQUIRED_VARS.items():
            print(f"{var}=  # {desc}")
        print("\n# Optional:")
        for var, desc in OPTIONAL_VARS.items():
            print(f"# {var}=  # {desc}")
        return 1
    
    # Load .env
    load_dotenv(dotenv_path=env_file, override=True)
    print(f"📄 Checking .env file: {env_file}\n")
    
    # Check required variables
    missing = []
    present = []
    
    for var, (desc, alt_var) in REQUIRED_VARS.items():
        value = os.getenv(var)
        # Check alternative variable name if provided
        if (not value or value.strip() == "") and alt_var:
            value = os.getenv(alt_var)
            if value:
                var_display = f"{var} (or {alt_var})"
            else:
                var_display = var
        else:
            var_display = var
        
        if not value or value.strip() == "":
            missing.append((var_display, desc))
            print(f"❌ {var_display}: NOT SET")
            print(f"   {desc}")
        else:
            present.append(var)
            # Show first/last few chars for security
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✅ {var_display}: SET ({masked})")
    
    print()
    
    # Check optional variables
    print("Optional variables:")
    for var, desc in OPTIONAL_VARS.items():
        value = os.getenv(var)
        if value:
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"  ✅ {var}: SET ({masked})")
        else:
            print(f"  ⚠️  {var}: NOT SET (using default)")
    
    print()
    
    if missing:
        print("❌ Missing required variables:")
        for var, desc in missing:
            print(f"   - {var}: {desc}")
        print(f"\n📝 Add these to your .env file at: {env_file}")
        return 1
    else:
        print("✅ All required variables are set!")
        return 0

if __name__ == "__main__":
    exit(main())

