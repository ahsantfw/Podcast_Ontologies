"""
Reranking Module - RRF (Reciprocal Rank Fusion) + MMR (Maximal Marginal Relevance)

Implements multiple reranking strategies:
- RRF: Combines multiple ranked lists (RAG + KG)
- MMR: Promotes diversity while maintaining relevance
- Hybrid (RRF + MMR): Best of both worlds
"""
import os
from typing import List, Dict, Any, Optional, Literal
from collections import defaultdict
import numpy as np
from core_engine.logging import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


class Reranker:
    """
    Reranker supporting multiple strategies:
    - RRF: Reciprocal Rank Fusion (combines multiple ranked lists)
    - MMR: Maximal Marginal Relevance (promotes diversity)
    - Hybrid: RRF + MMR (best of both worlds)
    
    RRF Formula: RRF_score = sum(1 / (k + rank)) for each list
    MMR Formula: MMR = λ * Relevance(query, doc) - (1-λ) * max_similarity(doc, selected_docs)
    """
    
    def __init__(
        self,
        strategy: Literal["rrf", "mmr", "rrf_mmr"] = "rrf_mmr",
        k: int = 60,
        lambda_param: float = 0.5,
        openai_client=None,
        embed_model: str = "text-embedding-3-large",
    ):
        """
        Initialize reranker.
        
        Args:
            strategy: Reranking strategy - "rrf", "mmr", or "rrf_mmr" (hybrid)
            k: RRF constant (default 60, standard value)
            lambda_param: MMR lambda parameter (0.0-1.0, default 0.5)
                          Higher = more relevance, Lower = more diversity
            openai_client: OpenAI client for embeddings (required for MMR)
            embed_model: Embedding model name (default: text-embedding-3-large)
        """
        self.strategy = strategy.lower()
        self.k = k
        self.lambda_param = lambda_param
        self.openai_client = openai_client
        self.embed_model = embed_model
        self.logger = get_logger(__name__)
        
        # Validate strategy
        if self.strategy not in ["rrf", "mmr", "rrf_mmr"]:
            self.logger.warning(f"Invalid strategy '{strategy}', defaulting to 'rrf_mmr'")
            self.strategy = "rrf_mmr"
        
        # Check if OpenAI client is needed
        if self.strategy in ["mmr", "rrf_mmr"] and not self.openai_client:
            # Try to get from environment
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.openai_client = OpenAI(api_key=api_key)
                    self.logger.info("openai_client_initialized_for_mmr")
                else:
                    self.logger.warning("openai_client_not_available_for_mmr")
            except Exception as e:
                self.logger.warning(f"failed_to_init_openai_for_mmr: {e}")
    
    def rerank(
        self,
        rag_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using configured strategy.
        
        Args:
            rag_results: List of RAG results (already ranked)
            kg_results: List of KG results (already ranked)
            query: Query string (required for MMR)
        
        Returns:
            Reranked list of results
        """
        if not rag_results and not kg_results:
            return []
        
        # Route to appropriate strategy
        if self.strategy == "rrf":
            return self._rerank_rrf(rag_results, kg_results, query)
        elif self.strategy == "mmr":
            return self._rerank_mmr(rag_results, kg_results, query)
        elif self.strategy == "rrf_mmr":
            # Hybrid: RRF first, then MMR
            rrf_results = self._rerank_rrf(rag_results, kg_results, query)
            return self._rerank_mmr_on_results(rrf_results, query)
        else:
            # Fallback to RRF
            self.logger.warning(f"Unknown strategy '{self.strategy}', using RRF")
            return self._rerank_rrf(rag_results, kg_results, query)
    
    def _rerank_rrf(
        self,
        rag_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Rerank using RRF algorithm."""
        # Create result maps with unique identifiers
        rag_map = self._create_result_map(rag_results, "rag")
        kg_map = self._create_result_map(kg_results, "kg")
        
        # Calculate RRF scores
        rrf_scores = defaultdict(float)
        
        # Score RAG results
        for rank, result_id in enumerate(rag_map.keys(), start=1):
            rrf_scores[result_id] += 1.0 / (self.k + rank)
        
        # Score KG results
        for rank, result_id in enumerate(kg_map.keys(), start=1):
            rrf_scores[result_id] += 1.0 / (self.k + rank)
        
        # Combine all results
        all_results = {**rag_map, **kg_map}
        
        # Sort by RRF score (descending)
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Build reranked list
        reranked = []
        seen_texts = set()  # Deduplication by text
        
        for result_id, score in sorted_results:
            if result_id in all_results:
                result = all_results[result_id].copy()
                result["rrf_score"] = score
                
                # Deduplicate by text content
                text_key = self._get_text_key(result)
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    reranked.append(result)
        
        self.logger.info(
            "rrf_rerank_complete",
            extra={
                "context": {
                    "rag_count": len(rag_results),
                    "kg_count": len(kg_results),
                    "reranked_count": len(reranked),
                    "query": query[:50] if query else None,
                }
            }
        )
        
        return reranked
    
    def _rerank_mmr(
        self,
        rag_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Rerank using MMR algorithm."""
        if not query:
            self.logger.warning("mmr_requires_query_fallback_to_rrf")
            return self._rerank_rrf(rag_results, kg_results, query)
        
        if not self.openai_client:
            self.logger.warning("mmr_requires_openai_fallback_to_rrf")
            return self._rerank_rrf(rag_results, kg_results, query)
        
        # Combine results
        all_results = []
        for result in rag_results:
            all_results.append({**result, "source_type": "rag"})
        for result in kg_results:
            all_results.append({**result, "source_type": "kg"})
        
        if not all_results:
            return []
        
        # Get query embedding
        try:
            query_embedding = self._get_embedding(query)
        except Exception as e:
            self.logger.error(f"mmr_query_embedding_failed: {e}, fallback_to_rrf")
            return self._rerank_rrf(rag_results, kg_results, query)
        
        # Get embeddings for all results
        result_embeddings = {}
        for idx, result in enumerate(all_results):
            try:
                text = self._get_result_text(result)
                result_embeddings[idx] = self._get_embedding(text)
            except Exception as e:
                self.logger.warning(f"mmr_result_embedding_failed_for_idx_{idx}: {e}")
                # Use zero vector as fallback
                result_embeddings[idx] = np.zeros(3072)  # text-embedding-3-large dimension
        
        # MMR selection
        selected = []
        remaining = list(range(len(all_results)))
        
        # Select first result (highest relevance)
        if remaining:
            first_idx = max(
                remaining,
                key=lambda i: self._cosine_similarity(query_embedding, result_embeddings[i])
            )
            selected.append(first_idx)
            remaining.remove(first_idx)
        
        # Select remaining results using MMR
        while remaining and len(selected) < len(all_results):
            best_idx = None
            best_score = float('-inf')
            
            for idx in remaining:
                # Relevance score
                relevance = self._cosine_similarity(query_embedding, result_embeddings[idx])
                
                # Diversity penalty (max similarity to already selected)
                max_similarity = 0.0
                if selected:
                    max_similarity = max(
                        self._cosine_similarity(result_embeddings[idx], result_embeddings[sel_idx])
                        for sel_idx in selected
                    )
                
                # MMR score
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)
        
        # Build reranked list in MMR order
        reranked = []
        seen_texts = set()
        
        for idx in selected:
            result = all_results[idx].copy()
            result["mmr_score"] = best_score if idx == selected[-1] else None
            
            # Deduplicate
            text_key = self._get_text_key(result)
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                reranked.append(result)
        
        self.logger.info(
            "mmr_rerank_complete",
            extra={
                "context": {
                    "rag_count": len(rag_results),
                    "kg_count": len(kg_results),
                    "reranked_count": len(reranked),
                    "query": query[:50],
                }
            }
        )
        
        return reranked
    
    def _rerank_mmr_on_results(
        self,
        rrf_results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Apply MMR to already RRF-ranked results (hybrid approach)."""
        if not query or not self.openai_client:
            # If MMR can't be applied, return RRF results
            return rrf_results
        
        if len(rrf_results) <= 1:
            return rrf_results
        
        # Apply MMR to top N results (to keep it fast)
        top_n = min(20, len(rrf_results))
        top_results = rrf_results[:top_n]
        remaining_results = rrf_results[top_n:]
        
        # Get query embedding
        try:
            query_embedding = self._get_embedding(query)
        except Exception as e:
            self.logger.warning(f"hybrid_mmr_query_embedding_failed: {e}, using_rrf_only")
            return rrf_results
        
        # Get embeddings for top results
        result_embeddings = {}
        for idx, result in enumerate(top_results):
            try:
                text = self._get_result_text(result)
                result_embeddings[idx] = self._get_embedding(text)
            except Exception as e:
                self.logger.warning(f"hybrid_mmr_result_embedding_failed_for_idx_{idx}: {e}")
                result_embeddings[idx] = np.zeros(3072)
        
        # MMR selection on top results
        selected = []
        remaining = list(range(len(top_results)))
        
        # First result (highest RRF score)
        if remaining:
            first_idx = max(
                remaining,
                key=lambda i: self._cosine_similarity(query_embedding, result_embeddings[i])
            )
            selected.append(first_idx)
            remaining.remove(first_idx)
        
        # Select remaining using MMR
        while remaining:
            best_idx = None
            best_score = float('-inf')
            
            for idx in remaining:
                relevance = self._cosine_similarity(query_embedding, result_embeddings[idx])
                max_similarity = max(
                    self._cosine_similarity(result_embeddings[idx], result_embeddings[sel_idx])
                    for sel_idx in selected
                ) if selected else 0.0
                
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)
        
        # Build final list: MMR-reranked top results + remaining RRF results
        reranked = []
        seen_texts = set()
        
        for idx in selected:
            result = top_results[idx].copy()
            result["hybrid_score"] = "rrf_mmr"
            text_key = self._get_text_key(result)
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                reranked.append(result)
        
        # Add remaining RRF results
        for result in remaining_results:
            text_key = self._get_text_key(result)
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                reranked.append(result)
        
        self.logger.info(
            "hybrid_rrf_mmr_rerank_complete",
            extra={
                "context": {
                    "reranked_count": len(reranked),
                    "mmr_top_n": top_n,
                    "query": query[:50],
                }
            }
        )
        
        return reranked
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not available")
        
        response = self.openai_client.embeddings.create(
            model=self.embed_model,
            input=text[:8000]  # Limit text length
        )
        return np.array(response.data[0].embedding)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _get_result_text(self, result: Dict[str, Any]) -> str:
        """Extract text from result for embedding."""
        # For RAG results
        text = result.get("text", "")
        if text:
            return text[:8000]
        
        # For KG results
        concept = result.get("concept", "")
        desc = result.get("description", "")
        if concept or desc:
            return f"{concept}: {desc}"[:8000]
        
        # Fallback
        return str(result)[:8000]
    
    def _create_result_map(
        self,
        results: List[Dict[str, Any]],
        source_type: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create a map of results with unique identifiers.
        
        Args:
            results: List of results
            source_type: Source type ("rag" or "kg")
        
        Returns:
            Dictionary mapping result_id to result dict
        """
        result_map = {}
        
        for idx, result in enumerate(results):
            # Create unique ID based on content and source
            result_id = self._generate_result_id(result, source_type, idx)
            
            # Add source type to result
            result_with_type = result.copy()
            result_with_type["source_type"] = source_type
            
            result_map[result_id] = result_with_type
        
        return result_map
    
    def _generate_result_id(
        self,
        result: Dict[str, Any],
        source_type: str,
        index: int
    ) -> str:
        """
        Generate unique identifier for a result.
        
        Uses text content + metadata to create stable ID.
        """
        # For RAG: use text + episode_id + timestamp
        if source_type == "rag":
            text = result.get("text", "")[:100]
            metadata = result.get("metadata", {})
            episode_id = metadata.get("episode_id", "")
            timestamp = metadata.get("timestamp", "")
            return f"rag:{episode_id}:{timestamp}:{hash(text)}"
        
        # For KG: use concept + description
        elif source_type == "kg":
            concept = result.get("concept", "")
            desc = result.get("description", "")[:100]
            return f"kg:{concept}:{hash(desc)}"
        
        # Fallback
        return f"{source_type}:{index}:{hash(str(result))}"
    
    def _get_text_key(self, result: Dict[str, Any]) -> str:
        """
        Get text key for deduplication.
        
        Returns:
            Normalized text key for comparison
        """
        # For RAG results
        text = result.get("text", "")
        if text:
            return text[:200].lower().strip()
        
        # For KG results
        concept = result.get("concept", "")
        desc = result.get("description", "")
        if concept or desc:
            return f"{concept}:{desc}".lower().strip()[:200]
        
        # Fallback
        return str(result)[:200]


def rerank_results(
    rag_results: List[Dict[str, Any]],
    kg_results: List[Dict[str, Any]],
    query: Optional[str] = None,
    strategy: Literal["rrf", "mmr", "rrf_mmr"] = "rrf_mmr",
    k: int = 60,
    lambda_param: float = 0.5,
    openai_client=None,
    embed_model: str = "text-embedding-3-large",
) -> List[Dict[str, Any]]:
    """
    Convenience function to rerank results using configurable strategy.
    
    Args:
        rag_results: List of RAG results
        kg_results: List of KG results
        query: Query string (required for MMR)
        strategy: Reranking strategy - "rrf", "mmr", or "rrf_mmr"
        k: RRF constant (default 60)
        lambda_param: MMR lambda parameter (default 0.5)
        openai_client: OpenAI client (required for MMR)
        embed_model: Embedding model name
    
    Returns:
        Reranked list of results
    """
    reranker = Reranker(
        strategy=strategy,
        k=k,
        lambda_param=lambda_param,
        openai_client=openai_client,
        embed_model=embed_model,
    )
    return reranker.rerank(rag_results, kg_results, query)
