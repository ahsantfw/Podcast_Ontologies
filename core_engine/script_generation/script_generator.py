"""
Script Generator - Main orchestrator for script generation.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from core_engine.script_generation.theme_extractor import ThemeExtractor
from core_engine.script_generation.quote_compiler import QuoteCompiler
from core_engine.script_generation.narrative_builder import NarrativeBuilder
from core_engine.script_generation.formatter import ScriptFormatter
from core_engine.logging import get_logger

logger = get_logger(__name__)


class ScriptGenerator:
    """Generate tapestry-style scripts from Knowledge Graph."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.theme_extractor = ThemeExtractor(workspace_id)
        self.quote_compiler = QuoteCompiler()
        self.narrative_builder = NarrativeBuilder()
        self.formatter = ScriptFormatter()
    
    def generate(
        self,
        theme: str,
        episodes: Optional[List[str]] = None,
        runtime_minutes: int = 45,
        style: str = "tapestry",
        max_quotes: int = 20,
        output_format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate a script from Knowledge Graph.
        
        Args:
            theme: Theme/topic (e.g., "creativity", "discipline")
            episodes: Optional list of episode IDs to include
            runtime_minutes: Target runtime (default: 45)
            style: Script style - "tapestry" (interweaving), "thematic" (by theme), "linear" (chronological)
            max_quotes: Maximum quotes to include
            output_format: Output format - "markdown", "json", "plain"
            
        Returns:
            Dictionary with:
            - script: Script object
            - formatted: Formatted script string
            - metadata: Generation metadata
        """
        logger.info("generating_script", extra={
            "theme": theme,
            "episodes": episodes,
            "runtime": runtime_minutes,
            "style": style
        })
        
        # Step 1: Extract theme content
        theme_content = self.theme_extractor.extract_theme_content(
            theme=theme,
            episodes=episodes,
            max_quotes=max_quotes * 2  # Get more quotes for filtering
        )
        
        if not theme_content["quotes"]:
            # Provide helpful error message with suggestions
            concepts_found = theme_content.get("total_concepts", 0)
            if concepts_found > 0:
                raise ValueError(
                    f"No quotes found for theme: '{theme}'. Found {concepts_found} related concepts, "
                    "but no quotes were extracted. This may mean:\n"
                    "1. Quotes were not extracted during processing\n"
                    "2. Quotes exist but aren't linked to this theme\n"
                    "3. Try a more specific theme or re-process transcripts"
                )
            else:
                raise ValueError(
                    f"No content found for theme: '{theme}'. This may mean:\n"
                    "1. The theme doesn't appear in your knowledge graph\n"
                    "2. No transcripts have been processed yet\n"
                    "3. Try a different theme or upload/process transcripts first"
                )
        
        # Step 2: Compile quotes
        compiled_quotes = self.quote_compiler.compile_quotes(
            quotes=theme_content["quotes"],
            theme=theme,
            max_quotes=max_quotes
        )
        
        if not compiled_quotes:
            raise ValueError(f"No valid quotes compiled for theme: {theme}")
        
        # Step 3: Build narrative structure
        script = self.narrative_builder.build_script(
            quotes=compiled_quotes,
            theme=theme,
            concepts=theme_content["concepts"],
            runtime_minutes=runtime_minutes,
            style=style
        )
        
        # Step 4: Format script
        formatted = self.formatter.format(script, output_format)
        
        # Metadata
        metadata = {
            "theme": theme,
            "runtime_minutes": runtime_minutes,
            "style": style,
            "total_quotes": len(compiled_quotes),
            "total_segments": len(script.segments),
            "episodes": script.episodes,
            "concepts_found": theme_content["total_concepts"],
            "quotes_found": theme_content["total_quotes"]
        }
        
        return {
            "script": script,
            "formatted": formatted,
            "metadata": metadata
        }
    
    def generate_and_save(
        self,
        theme: str,
        output_path: str,
        episodes: Optional[List[str]] = None,
        runtime_minutes: int = 45,
        style: str = "tapestry",
        max_quotes: int = 20,
        output_format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate script and save to file.
        
        Args:
            theme: Theme/topic
            output_path: Path to save script file
            episodes: Optional list of episode IDs
            runtime_minutes: Target runtime
            style: Script style
            max_quotes: Maximum quotes
            output_format: Output format
            
        Returns:
            Generation result dictionary
        """
        result = self.generate(
            theme=theme,
            episodes=episodes,
            runtime_minutes=runtime_minutes,
            style=style,
            max_quotes=max_quotes,
            output_format=output_format
        )
        
        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.formatter.save(
            result["script"],
            str(output_file),
            output_format
        )
        
        logger.info("script_generated_and_saved", extra={
            "theme": theme,
            "output_path": output_path,
            "quotes": result["metadata"]["total_quotes"]
        })
        
        return result
    
    def close(self):
        """Close connections."""
        if self.theme_extractor:
            self.theme_extractor.close()

