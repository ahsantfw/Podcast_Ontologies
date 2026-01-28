"""
Query Expander

Generates query variations to improve retrieval coverage:
- Synonyms and rephrasing
- Different question formats
- Context-aware variations

Only used for moderate/complex queries (per query plan).
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from core_engine.logging import get_logger

load_dotenv()
logger = get_logger(__name__)

# Try to import OpenAI, make it optional
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - query expansion will be limited")


class QueryExpander:
    """
    Expands queries into variations for better retrieval coverage.
    
    Features:
    - LLM-based variation generation (synonyms, rephrasing)
    - Pattern-based fallback (if LLM unavailable)
    - Context-aware expansion
    - Result merging and deduplication
    """
    
    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
        max_variations: int = 3,
        use_llm: bool = True,
    ):
        """
        Initialize Query Expander.
        
        Args:
            openai_client: OpenAI client for LLM-based expansion (optional)
            max_variations: Maximum number of variations to generate
            use_llm: Whether to use LLM for expansion (default: True)
        """
        self.max_variations = max_variations
        self.use_llm = use_llm
        
        # Initialize OpenAI client if not provided
        if openai_client:
            self.openai_client = openai_client
        else:
            if OPENAI_AVAILABLE and use_llm:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.openai_client = OpenAI(api_key=api_key)
                else:
                    self.openai_client = None
                    logger.warning("OpenAI API key not found - using pattern-based expansion")
            else:
                self.openai_client = None
                logger.info("Using pattern-based query expansion (LLM not available)")
    
    def expand(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Generate query variations.
        
        Args:
            query: Original query
            context: Optional context (conversation history, query type, etc.)
        
        Returns:
            List of query variations (including original)
        """
        if not query or not query.strip():
            return []
        
        variations = [query]  # Always include original
        
        # Use LLM for intelligent expansion if available
        if self.openai_client and self.use_llm:
            llm_variations = self._expand_with_llm(query, context)
            variations.extend(llm_variations)
        else:
            # Fallback to pattern-based expansion
            pattern_variations = self._expand_pattern_based(query)
            variations.extend(pattern_variations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            v_lower = v.lower().strip()
            if v_lower and v_lower not in seen:
                seen.add(v_lower)
                unique_variations.append(v)
        
        # Limit to max_variations (including original)
        return unique_variations[:self.max_variations + 1]
    
    def _expand_with_llm(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate query variations using LLM."""
        if not self.openai_client:
            return []
        
        try:
            # Build prompt for query expansion
            query_type = context.get("query_type", "general") if context else "general"
            complexity = context.get("complexity", "moderate") if context else "moderate"
            
            prompt = f"""You are a query expansion system for a podcast knowledge base about philosophy, creativity, coaching, and personal development.

Generate {self.max_variations} query variations that will help retrieve more relevant information.

Original query: "{query}"

Query type: {query_type}
Complexity: {complexity}

Generate variations that:
1. Use synonyms and related terms
2. Rephrase in different question formats
3. Add context-specific terms (if relevant)
4. Maintain the core intent of the original query

Examples:
- "What is meditation?" → ["How is meditation defined?", "What does meditation involve?", "Tell me about meditation practices"]
- "What practices improve clarity?" → ["What methods enhance clarity?", "How can I achieve clarity?", "What techniques optimize clarity?"]

Return ONLY a JSON array of query strings:
{{"variations": ["variation1", "variation2", "variation3"]}}
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent variations
            )
            
            import json as json_module
            result = json_module.loads(response.choices[0].message.content)
            variations = result.get("variations", [])
            
            # Filter out variations that are too similar to original
            filtered = []
            query_lower = query.lower()
            for v in variations:
                v_lower = v.lower()
                # Skip if too similar (more than 80% overlap)
                if v_lower != query_lower:
                    filtered.append(v)
            
            logger.info(
                "query_expansion_llm",
                extra={
                    "context": {
                        "original": query[:50],
                        "variations_count": len(filtered),
                    }
                }
            )
            
            return filtered[:self.max_variations]
            
        except Exception as e:
            logger.warning(f"LLM query expansion failed: {e}")
            # Fallback to pattern-based
            return self._expand_pattern_based(query)
    
    def _expand_pattern_based(self, query: str) -> List[str]:
        """Generate query variations using patterns (fallback)."""
        variations = []
        query_lower = query.lower().strip()
        
        # Pattern 1: Question format variations
        if query_lower.startswith("what is"):
            # "What is X?" → "How is X defined?", "Tell me about X"
            entity = query[8:].strip().rstrip("?")
            variations.extend([
                f"How is {entity} defined?",
                f"Tell me about {entity}",
                f"What does {entity} involve?",
            ])
        elif query_lower.startswith("what are"):
            # "What are X?" → "Tell me about X", "What is X?"
            entity = query[8:].strip().rstrip("?")
            variations.extend([
                f"Tell me about {entity}",
                f"What is {entity}?",
            ])
        elif query_lower.startswith("how does"):
            # "How does X relate to Y?" → "What is the relationship between X and Y?"
            rest = query[8:].strip().rstrip("?")
            variations.extend([
                f"What is the relationship between {rest}?",
                f"Tell me about {rest}",
            ])
        elif query_lower.startswith("who is"):
            # "Who is X?" → "Tell me about X", "What is X?"
            entity = query[6:].strip().rstrip("?")
            variations.extend([
                f"Tell me about {entity}",
                f"What is {entity}?",
            ])
        
        # Pattern 2: Add context phrases
        if "practice" in query_lower or "method" in query_lower:
            variations.append(f"Tell me more about {query.rstrip('?')}")
        
        # Pattern 3: Synonym-based (simple)
        synonym_replacements = {
            "improve": ["enhance", "optimize", "boost"],
            "practice": ["method", "technique", "approach"],
            "relate": ["connect", "link", "associate"],
        }
        
        for word, synonyms in synonym_replacements.items():
            if word in query_lower:
                for synonym in synonyms[:1]:  # Use first synonym only
                    variation = query_lower.replace(word, synonym)
                    if variation != query_lower:
                        variations.append(variation.capitalize() + ("?" if "?" not in variation else ""))
        
        # Limit variations
        return variations[:self.max_variations]
    
    def expand_and_retrieve(
        self,
        query: str,
        retriever,
        context: Optional[Dict[str, Any]] = None,
        skip_original: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Expand query and retrieve results from all variations.
        
        Args:
            query: Original query
            retriever: HybridRetriever instance
            context: Optional context
            skip_original: If True, skip retrieving from original query (to avoid duplicates)
        
        Returns:
            Merged and deduplicated results from all variations
        """
        # Generate variations
        variations = self.expand(query, context)
        
        if not variations:
            return []
        
        # If skip_original, remove original query from variations (it's first in list)
        if skip_original and variations and variations[0].lower().strip() == query.lower().strip():
            variations = variations[1:]
        
        if not variations:
            return []
        
        logger.info(
            "query_expansion_start",
            extra={
                "context": {
                    "original": query[:50],
                    "variations_count": len(variations),
                    "skip_original": skip_original,
                }
            }
        )
        
        # Retrieve from all variations
        all_results = []
        seen_results = set()  # For deduplication
        
        for variation in variations:
            try:
                results = retriever.retrieve(variation, use_vector=True, use_graph=False)
                
                for result in results:
                    # Create unique key for deduplication
                    result_key = self._get_result_key(result)
                    if result_key not in seen_results:
                        seen_results.add(result_key)
                        all_results.append(result)
                        
            except Exception as e:
                logger.warning(
                    "query_expansion_retrieval_failed",
                    extra={"context": {"variation": variation[:50], "error": str(e)}}
                )
        
        logger.info(
            "query_expansion_complete",
            extra={
                "context": {
                    "original": query[:50],
                    "variations_used": len(variations),
                    "total_results": len(all_results),
                    "unique_results": len(seen_results),
                }
            }
        )
        
        return all_results
    
    def _get_result_key(self, result: Dict[str, Any]) -> str:
        """Generate unique key for result deduplication."""
        # Use text content as key (first 100 chars)
        text = result.get("text", result.get("content", ""))
        if text:
            return text[:100].lower().strip()
        
        # Fallback to ID if available
        result_id = result.get("id") or result.get("chunk_id")
        if result_id:
            return str(result_id)
        
        # Last resort: use full result hash
        return str(hash(str(result)))


# Convenience function
def expand_query(
    query: str,
    openai_client: Optional[OpenAI] = None,
    max_variations: int = 3,
    context: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Convenience function to expand a query.
    
    Args:
        query: Original query
        openai_client: OpenAI client (optional)
        max_variations: Maximum variations to generate
        context: Optional context
    
    Returns:
        List of query variations
    """
    expander = QueryExpander(
        openai_client=openai_client,
        max_variations=max_variations,
    )
    
    return expander.expand(query, context)
