"""
Quote Compiler - Compile and rank quotes for script generation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from core_engine.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CompiledQuote:
    """A quote compiled for script generation."""
    text: str
    speaker: Optional[str]
    episode_id: str
    timestamp: Optional[str]
    source_path: str
    start_char: int
    end_char: int
    related_concept: Optional[str] = None
    relevance_score: float = 0.0
    quality_score: float = 0.0


class QuoteCompiler:
    """Compile and rank quotes for script generation."""
    
    def __init__(self):
        pass
    
    def compile_quotes(
        self,
        quotes: List[Dict[str, Any]],
        theme: str,
        max_quotes: int = 20,
        min_length: int = 20,
        max_length: int = 500
    ) -> List[CompiledQuote]:
        """
        Compile and rank quotes for script generation.
        
        Args:
            quotes: Raw quotes from theme extractor
            theme: Theme/topic for relevance scoring
            max_quotes: Maximum quotes to return
            min_length: Minimum quote length (characters)
            max_length: Maximum quote length (characters)
            
        Returns:
            List of compiled quotes, sorted by relevance and quality
        """
        logger.info("compiling_quotes", extra={"total_quotes": len(quotes), "theme": theme})
        
        compiled = []
        
        for quote in quotes:
            # Filter by length
            text = quote.get("text", "").strip()
            if len(text) < min_length or len(text) > max_length:
                continue
            
            # Calculate scores
            relevance_score = self._calculate_relevance(text, theme)
            quality_score = self._calculate_quality(text, quote)
            
            compiled_quote = CompiledQuote(
                text=text,
                speaker=quote.get("speaker"),
                episode_id=quote.get("episode_id", ""),
                timestamp=quote.get("timestamp"),
                source_path=quote.get("source_path", ""),
                start_char=quote.get("start_char", 0),
                end_char=quote.get("end_char", 0),
                related_concept=quote.get("related_concept"),
                relevance_score=relevance_score,
                quality_score=quality_score
            )
            
            compiled.append(compiled_quote)
        
        # Sort by combined score (relevance + quality)
        compiled.sort(
            key=lambda q: q.relevance_score + q.quality_score,
            reverse=True
        )
        
        # Remove duplicates (same text from same episode)
        unique_quotes = self._deduplicate_quotes(compiled)
        
        return unique_quotes[:max_quotes]
    
    def _calculate_relevance(self, text: str, theme: str) -> float:
        """Calculate relevance score (0-1) based on theme match."""
        text_lower = text.lower()
        theme_lower = theme.lower()
        
        # Exact match
        if theme_lower in text_lower:
            return 1.0
        
        # Word match
        theme_words = theme_lower.split()
        matches = sum(1 for word in theme_words if word in text_lower)
        if theme_words:
            return matches / len(theme_words)
        
        return 0.5
    
    def _calculate_quality(self, text: str, quote: Dict[str, Any]) -> float:
        """Calculate quality score (0-1) based on quote characteristics."""
        score = 0.5  # Base score
        
        # Length bonus (optimal length: 50-200 chars)
        length = len(text)
        if 50 <= length <= 200:
            score += 0.2
        elif 20 <= length <= 300:
            score += 0.1
        
        # Has speaker
        if quote.get("speaker"):
            score += 0.1
        
        # Has timestamp
        if quote.get("timestamp"):
            score += 0.1
        
        # Has related concept
        if quote.get("related_concept"):
            score += 0.1
        
        # Check for complete sentences
        if text.endswith(('.', '!', '?')):
            score += 0.1
        
        return min(score, 1.0)
    
    def _deduplicate_quotes(self, quotes: List[CompiledQuote]) -> List[CompiledQuote]:
        """Remove duplicate quotes (same text from same episode)."""
        seen = set()
        unique = []
        
        for quote in quotes:
            key = (quote.text.lower()[:100], quote.episode_id)  # First 100 chars + episode
            if key not in seen:
                seen.add(key)
                unique.append(quote)
        
        return unique
    
    def group_quotes_by_speaker(
        self,
        quotes: List[CompiledQuote]
    ) -> Dict[str, List[CompiledQuote]]:
        """Group quotes by speaker."""
        grouped = {}
        
        for quote in quotes:
            speaker = quote.speaker or "Unknown"
            if speaker not in grouped:
                grouped[speaker] = []
            grouped[speaker].append(quote)
        
        return grouped
    
    def group_quotes_by_episode(
        self,
        quotes: List[CompiledQuote]
    ) -> Dict[str, List[CompiledQuote]]:
        """Group quotes by episode."""
        grouped = {}
        
        for quote in quotes:
            episode = quote.episode_id or "Unknown"
            if episode not in grouped:
                grouped[episode] = []
            grouped[episode].append(quote)
        
        return grouped

