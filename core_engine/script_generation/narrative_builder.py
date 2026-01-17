"""
Narrative Builder - Build narrative structure from quotes and concepts.
Uses LLM to create flowing, interweaving narratives like "The Midnight Miracle".
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from core_engine.script_generation.quote_compiler import CompiledQuote
from core_engine.logging import get_logger

logger = get_logger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai_not_available", extra={"message": "LLM features disabled"})


@dataclass
class ScriptSegment:
    """A segment in the script."""
    title: str
    start_time: str  # Format: "MM:SS"
    end_time: str
    quotes: List[CompiledQuote] = field(default_factory=list)
    narration: Optional[str] = None
    music_cue: Optional[str] = None
    transition: Optional[str] = None


@dataclass
class Script:
    """Complete script structure."""
    title: str
    theme: str
    runtime_minutes: int
    segments: List[ScriptSegment] = field(default_factory=list)
    episodes: List[str] = field(default_factory=list)
    style: str = "tapestry"  # tapestry, linear, thematic


class NarrativeBuilder:
    """Build narrative structure from quotes and concepts.
    Uses LLM to create flowing, interweaving narratives with transitions."""
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and OPENAI_AVAILABLE
        if self.use_llm:
            self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            self.llm_client = None
    
    def build_script(
        self,
        quotes: List[CompiledQuote],
        theme: str,
        concepts: List[Dict[str, Any]],
        runtime_minutes: int = 45,
        style: str = "tapestry"
    ) -> Script:
        """
        Build script structure from quotes and concepts.
        
        Args:
            quotes: Compiled quotes
            theme: Theme/topic
            concepts: Related concepts
            runtime_minutes: Target runtime
            style: Script style (tapestry, linear, thematic)
            
        Returns:
            Script structure
        """
        logger.info("building_script", extra={
            "theme": theme,
            "quotes": len(quotes),
            "runtime": runtime_minutes,
            "style": style
        })
        
        # Calculate time allocation
        total_seconds = runtime_minutes * 60
        intro_time = 30  # 30 seconds intro
        outro_time = 30  # 30 seconds outro
        available_time = total_seconds - intro_time - outro_time
        
        # Estimate quote time (average 15 seconds per quote)
        avg_quote_time = 15
        max_quotes = min(len(quotes), available_time // avg_quote_time)
        quotes_to_use = quotes[:max_quotes]
        
        # Build segments
        if style == "tapestry":
            segments = self._build_tapestry_structure(quotes_to_use, theme, available_time)
        elif style == "thematic":
            segments = self._build_thematic_structure(quotes_to_use, concepts, available_time)
        else:
            segments = self._build_linear_structure(quotes_to_use, available_time)
        
        # Add intro and outro
        intro_segment = ScriptSegment(
            title="INTRO",
            start_time="00:00",
            end_time=self._format_time(intro_time),
            narration=self._generate_intro(theme, quotes_to_use),
            music_cue="Ambient intro, fade in"
        )
        
        outro_segment = ScriptSegment(
            title="CONCLUSION",
            start_time=self._format_time(total_seconds - outro_time),
            end_time=self._format_time(total_seconds),
            narration=self._generate_outro(theme, quotes_to_use),
            music_cue="Outro, fade out"
        )
        
        # Collect episode IDs
        episodes = list(set(q.episode_id for q in quotes_to_use if q.episode_id))
        
        script = Script(
            title=f"The Nature of {theme.title()}",
            theme=theme,
            runtime_minutes=runtime_minutes,
            segments=[intro_segment] + segments + [outro_segment],
            episodes=episodes,
            style=style
        )
        
        return script
    
    def _build_tapestry_structure(
        self,
        quotes: List[CompiledQuote],
        theme: str,
        available_time: int
    ) -> List[ScriptSegment]:
        """Build tapestry-style structure (interweaving quotes with narrative flow)."""
        segments = []
        
        # Group quotes by speaker for variety
        from collections import defaultdict
        by_speaker = defaultdict(list)
        for quote in quotes:
            speaker = quote.speaker or "Unknown"
            by_speaker[speaker].append(quote)
        
        # Distribute quotes across segments (3-5 segments)
        num_segments = min(5, max(3, len(quotes) // 3))
        quotes_per_segment = len(quotes) // num_segments
        
        current_time = 30  # Start after intro
        segment_time = available_time // num_segments
        
        for i in range(num_segments):
            start_idx = i * quotes_per_segment
            end_idx = start_idx + quotes_per_segment if i < num_segments - 1 else len(quotes)
            segment_quotes = quotes[start_idx:end_idx]
            
            if not segment_quotes:
                continue
            
            # Generate transitions between quotes using LLM
            transitions = self._generate_transitions(segment_quotes, theme) if self.use_llm else None
            
            # Create segment with narrative flow
            segment = ScriptSegment(
                title=f"SEGMENT {i+1}: {self._generate_segment_title(segment_quotes, theme)}",
                start_time=self._format_time(current_time),
                end_time=self._format_time(current_time + segment_time),
                quotes=segment_quotes,
                music_cue="Transition music" if i > 0 else None,
                transition=transitions  # Add narrative transitions
            )
            
            segments.append(segment)
            current_time += segment_time
        
        return segments
    
    def _build_thematic_structure(
        self,
        quotes: List[CompiledQuote],
        concepts: List[Dict[str, Any]],
        available_time: int
    ) -> List[ScriptSegment]:
        """Build thematic structure (grouped by sub-themes)."""
        # Group quotes by related concept
        from collections import defaultdict
        by_concept = defaultdict(list)
        for quote in quotes:
            concept = quote.related_concept or "General"
            by_concept[concept].append(quote)
        
        # Create segments for each concept
        segments = []
        num_concepts = len(by_concept)
        segment_time = available_time // num_concepts if num_concepts > 0 else available_time
        
        current_time = 30
        
        for i, (concept, concept_quotes) in enumerate(by_concept.items()):
            segment = ScriptSegment(
                title=f"SEGMENT {i+1}: {concept}",
                start_time=self._format_time(current_time),
                end_time=self._format_time(current_time + segment_time),
                quotes=concept_quotes[:5],  # Max 5 quotes per segment
                music_cue="Transition music" if i > 0 else None
            )
            
            segments.append(segment)
            current_time += segment_time
        
        return segments
    
    def _build_linear_structure(
        self,
        quotes: List[CompiledQuote],
        available_time: int
    ) -> List[ScriptSegment]:
        """Build linear structure (chronological)."""
        segments = []
        
        # Sort quotes by timestamp if available
        sorted_quotes = sorted(quotes, key=lambda q: q.timestamp or "")
        
        num_segments = min(5, max(3, len(sorted_quotes) // 3))
        quotes_per_segment = len(sorted_quotes) // num_segments
        segment_time = available_time // num_segments
        
        current_time = 30
        
        for i in range(num_segments):
            start_idx = i * quotes_per_segment
            end_idx = start_idx + quotes_per_segment if i < num_segments - 1 else len(sorted_quotes)
            segment_quotes = sorted_quotes[start_idx:end_idx]
            
            if not segment_quotes:
                continue
            
            segment = ScriptSegment(
                title=f"SEGMENT {i+1}",
                start_time=self._format_time(current_time),
                end_time=self._format_time(current_time + segment_time),
                quotes=segment_quotes,
                music_cue="Transition music" if i > 0 else None
            )
            
            segments.append(segment)
            current_time += segment_time
        
        return segments
    
    def _generate_segment_title(self, quotes: List[CompiledQuote], theme: str) -> str:
        """Generate title for segment based on quotes."""
        # Use first quote's related concept or theme
        if quotes and quotes[0].related_concept:
            return quotes[0].related_concept
        return theme.title()
    
    def _generate_intro(self, theme: str, quotes: List[CompiledQuote]) -> str:
        """Generate intro narration using LLM for better flow."""
        num_episodes = len(set(q.episode_id for q in quotes if q.episode_id))
        speakers = list(set(q.speaker for q in quotes if q.speaker))[:3]
        
        if self.use_llm and self.llm_client:
            try:
                prompt = f"""You are writing an intro for a podcast episode about "{theme}".

The episode features insights from {num_episodes} conversations with {', '.join(speakers) if speakers else 'various guests'}.

Write a compelling, conversational intro (2-3 sentences) that:
- Introduces the theme naturally
- Sets up the interweaving of different voices
- Creates intrigue and flow
- Sounds like "The Midnight Miracle" podcast style

Write ONLY the intro text, no labels or formatting:"""
                
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a skilled podcast script writer who creates flowing, conversational narratives."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                
                intro = response.choices[0].message.content.strip()
                return intro
            except Exception as e:
                logger.warning("llm_intro_failed", extra={"error": str(e)})
        
        # Fallback to template
        intro = f"What is {theme}? Across {num_episodes} conversations, we've explored "
        intro += f"the many facets of {theme}. Today, we weave together insights from "
        intro += f"different voices, all connected by a shared understanding of what "
        intro += f"{theme} means."
        
        return intro
    
    def _generate_outro(self, theme: str, quotes: List[CompiledQuote]) -> str:
        """Generate outro narration using LLM for better flow."""
        if self.use_llm and self.llm_client:
            try:
                # Get key insights from quotes
                key_quotes = [q.text[:100] for q in quotes[:3]]
                
                prompt = f"""You are writing a conclusion for a podcast episode about "{theme}".

The episode explored this theme through various perspectives. Key insights included:
{chr(10).join(f'- {q}...' for q in key_quotes)}

Write a compelling, thoughtful conclusion (2-3 sentences) that:
- Synthesizes the different perspectives
- Creates a sense of completion
- Leaves the listener with something to think about
- Sounds like "The Midnight Miracle" podcast style

Write ONLY the conclusion text, no labels or formatting:"""
                
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a skilled podcast script writer who creates flowing, conversational narratives."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                
                outro = response.choices[0].message.content.strip()
                return outro
            except Exception as e:
                logger.warning("llm_outro_failed", extra={"error": str(e)})
        
        # Fallback to template
        outro = f"As we've seen, {theme} takes many forms. But at its core, "
        outro += f"it's about connection, understanding, and discovery. These voices, "
        outro += f"though different, all point to the same truth: {theme} is not "
        outro += f"just a concept—it's a practice, a way of being."
        
        return outro
    
    def _generate_transitions(
        self,
        quotes: List[CompiledQuote],
        theme: str
    ) -> Optional[str]:
        """Generate narrative transitions between quotes using LLM."""
        if not self.use_llm or not self.llm_client or len(quotes) < 2:
            return None
        
        try:
            # Create context from quotes
            quote_context = []
            for i, quote in enumerate(quotes[:3], 1):  # Use first 3 quotes
                speaker = quote.speaker or "A guest"
                quote_context.append(f"Quote {i} ({speaker}): {quote.text[:150]}...")
            
            prompt = f"""You are writing transitions for a podcast episode about "{theme}".

The segment contains these quotes:
{chr(10).join(quote_context)}

Write brief, flowing transitions (1-2 sentences each) that:
- Connect the ideas naturally
- Create narrative flow between quotes
- Sound conversational, not mechanical
- Link themes and ideas together
- Style: Like "The Midnight Miracle" - interweaving, flowing, musical

Format as a single flowing narrative that connects these quotes. Write ONLY the transition text:"""
            
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a skilled podcast script writer who creates flowing, interweaving narratives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            transitions = response.choices[0].message.content.strip()
            return transitions
        except Exception as e:
            logger.warning("llm_transitions_failed", extra={"error": str(e)})
            return None
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds as MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

