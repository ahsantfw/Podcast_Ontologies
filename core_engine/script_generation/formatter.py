"""
Formatter - Format scripts for output (Markdown, JSON, etc.).
"""

from typing import Optional
from core_engine.script_generation.narrative_builder import Script, ScriptSegment
from core_engine.script_generation.quote_compiler import CompiledQuote
from core_engine.logging import get_logger

logger = get_logger(__name__)


class ScriptFormatter:
    """Format scripts for output."""
    
    def format(self, script: Script, format_type: str = "markdown") -> str:
        """
        Format script for output.
        
        Args:
            script: Script to format
            format_type: Output format (markdown, json, plain)
            
        Returns:
            Formatted script string
        """
        if format_type == "markdown":
            return self._format_markdown(script)
        elif format_type == "json":
            return self._format_json(script)
        else:
            return self._format_plain(script)
    
    def _format_markdown(self, script: Script) -> str:
        """Format as Markdown."""
        lines = []
        
        # Header
        lines.append(f"# Script: {script.title}")
        lines.append("")
        lines.append(f"**Runtime**: {script.runtime_minutes} minutes")
        lines.append(f"**Theme**: {script.theme}")
        lines.append(f"**Style**: {script.style}")
        lines.append(f"**Source Episodes**: {', '.join(script.episodes)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Segments
        for segment in script.segments:
            lines.append(f"## [{segment.start_time} - {segment.end_time}] {segment.title}")
            lines.append("")
            
            # Music cue
            if segment.music_cue:
                lines.append(f"*[Music: {segment.music_cue}]*")
                lines.append("")
            
            # Narration
            if segment.narration:
                lines.append(f"**Narrator**: {segment.narration}")
                lines.append("")
            
            # Quotes with narrative flow
            for i, quote in enumerate(segment.quotes, 1):
                # Add transition before quote (except first)
                if i > 1 and segment.transition:
                    # Use transition text to connect quotes
                    transition_parts = segment.transition.split('.')
                    if len(transition_parts) >= i - 1:
                        lines.append(f"*{transition_parts[i-2].strip()}*")
                        lines.append("")
                
                # Speaker info
                speaker_info = []
                if quote.speaker:
                    speaker_info.append(f"**{quote.speaker}**")
                if quote.episode_id:
                    speaker_info.append(f"({quote.episode_id})")
                if quote.timestamp:
                    speaker_info.append(f"[{quote.timestamp}]")
                
                if speaker_info:
                    lines.append("  " + " | ".join(speaker_info))
                    lines.append("")
                
                # Quote text (more conversational format)
                lines.append(f"  {quote.text}")
                lines.append("")
                
                # Related concept (subtle)
                if quote.related_concept and i == len(segment.quotes):
                    lines.append(f"  *[This connects to: {quote.related_concept}]*")
                    lines.append("")
            
            # Segment transition
            if segment.transition and len(segment.quotes) > 0:
                # Use transition to bridge to next segment
                lines.append(f"*{segment.transition}*")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # Sources
        lines.append("## Sources")
        lines.append("")
        for episode in script.episodes:
            lines.append(f"- Episode: {episode}")
        lines.append("")
        
        return "\n".join(lines)
    
    def _format_json(self, script: Script) -> str:
        """Format as JSON."""
        import json
        
        script_dict = {
            "title": script.title,
            "theme": script.theme,
            "runtime_minutes": script.runtime_minutes,
            "style": script.style,
            "episodes": script.episodes,
            "segments": [
                {
                    "title": segment.title,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "narration": segment.narration,
                    "music_cue": segment.music_cue,
                    "transition": segment.transition,
                    "quotes": [
                        {
                            "text": quote.text,
                            "speaker": quote.speaker,
                            "episode_id": quote.episode_id,
                            "timestamp": quote.timestamp,
                            "source_path": quote.source_path,
                            "related_concept": quote.related_concept
                        }
                        for quote in segment.quotes
                    ]
                }
                for segment in script.segments
            ]
        }
        
        return json.dumps(script_dict, indent=2)
    
    def _format_plain(self, script: Script) -> str:
        """Format as plain text."""
        lines = []
        
        lines.append(f"SCRIPT: {script.title}")
        lines.append(f"Runtime: {script.runtime_minutes} minutes")
        lines.append(f"Theme: {script.theme}")
        lines.append("")
        
        for segment in script.segments:
            lines.append(f"[{segment.start_time} - {segment.end_time}] {segment.title}")
            if segment.music_cue:
                lines.append(f"Music: {segment.music_cue}")
            if segment.narration:
                lines.append(f"Narrator: {segment.narration}")
            lines.append("")
            
            for quote in segment.quotes:
                lines.append(f"  {quote.speaker or 'Unknown'}: {quote.text}")
                if quote.timestamp:
                    lines.append(f"    [{quote.timestamp}]")
                lines.append("")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def save(self, script: Script, filepath: str, format_type: str = "markdown"):
        """Save script to file."""
        content = self.format(script, format_type)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("script_saved", extra={"filepath": filepath, "format": format_type})

