#!/usr/bin/env python3
"""
Script Generation CLI - Generate tapestry-style scripts from Knowledge Graph.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

load_dotenv()

from core_engine.script_generation import ScriptGenerator
from core_engine.logging import get_logger

logger = get_logger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate tapestry-style scripts from Knowledge Graph"
    )
    parser.add_argument(
        "theme",
        help="Theme/topic for script (e.g., 'creativity', 'discipline', 'overcoming obstacles')"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: scripts/{theme}_script.md)"
    )
    parser.add_argument(
        "--episodes", "-e",
        nargs="+",
        help="Specific episodes to include (optional)"
    )
    parser.add_argument(
        "--runtime", "-r",
        type=int,
        default=45,
        help="Runtime in minutes (default: 45)"
    )
    parser.add_argument(
        "--style", "-s",
        choices=["tapestry", "thematic", "linear"],
        default="tapestry",
        help="Script style: tapestry (interweaving), thematic (by theme), linear (chronological)"
    )
    parser.add_argument(
        "--max-quotes", "-q",
        type=int,
        default=20,
        help="Maximum quotes to include (default: 20)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "plain"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--workspace-id",
        default=os.getenv("WORKSPACE_ID", "default"),
        help="Workspace identifier"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview script without saving"
    )
    
    args = parser.parse_args()
    
    # Generate script
    print("=" * 70)
    print("🎬 SCRIPT GENERATION")
    print("=" * 70)
    print(f"Theme: {args.theme}")
    print(f"Runtime: {args.runtime} minutes")
    print(f"Style: {args.style}")
    print(f"Episodes: {args.episodes or 'All'}")
    print("=" * 70)
    print()
    
    try:
        generator = ScriptGenerator(workspace_id=args.workspace_id)
        
        print("🔍 Extracting theme content from Knowledge Graph...")
        result = generator.generate(
            theme=args.theme,
            episodes=args.episodes,
            runtime_minutes=args.runtime,
            style=args.style,
            max_quotes=args.max_quotes,
            output_format=args.format
        )
        
        print(f"✅ Script generated!")
        print(f"   - Quotes: {result['metadata']['total_quotes']}")
        print(f"   - Segments: {result['metadata']['total_segments']}")
        print(f"   - Episodes: {', '.join(result['metadata']['episodes'])}")
        print()
        
        # Preview or save
        if args.preview:
            print("=" * 70)
            print("📄 PREVIEW:")
            print("=" * 70)
            print(result["formatted"][:2000])  # First 2000 chars
            if len(result["formatted"]) > 2000:
                print("\n... (truncated, use --output to save full script)")
        else:
            # Determine output path
            if args.output:
                output_path = args.output
            else:
                output_dir = Path("scripts")
                output_dir.mkdir(exist_ok=True)
                safe_theme = args.theme.lower().replace(" ", "_")
                output_path = output_dir / f"{safe_theme}_script.{args.format if args.format != 'markdown' else 'md'}"
            
            # Save
            generator.formatter.save(
                result["script"],
                str(output_path),
                args.format
            )
            
            print(f"💾 Script saved to: {output_path}")
            print()
            print("=" * 70)
            print("📊 METADATA:")
            print("=" * 70)
            for key, value in result["metadata"].items():
                print(f"  {key}: {value}")
        
        generator.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("script_generation_failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

