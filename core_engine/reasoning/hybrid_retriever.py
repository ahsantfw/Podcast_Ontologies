"""
Hybrid retriever combining vector search (Qdrant) and graph traversal (Neo4j).
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

try:
    from qdrant_client import QdrantClient
    from openai import OpenAI
except ImportError:
    QdrantClient = None
    OpenAI = None

from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger
from core_engine.reasoning.embedding_cache import get_embedding_cache
from core_engine.reasoning.query_expander import QueryExpander


def load_env() -> None:
    """Load environment variables."""
    try:
        load_dotenv()
    except Exception:
        pass


class HybridRetriever:
    """Hybrid retriever combining vector and graph search."""

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        qdrant_collection: str = "ontology_chunks",
        embed_model: str = "text-embedding-3-large",
        workspace_id: Optional[str] = None,
        vector_weight: float = 0.5,
        graph_weight: float = 0.5,
        top_k: int = 10,
    ):
        """
        Initialize hybrid retriever.

        Args:
            neo4j_client: Neo4j client
            qdrant_url: Qdrant URL (default: from env)
            qdrant_api_key: Qdrant API key (default: from env)
            qdrant_collection: Qdrant collection name
            embed_model: Embedding model name
            workspace_id: Workspace identifier
            vector_weight: Weight for vector results (0-1)
            graph_weight: Weight for graph results (0-1)
            top_k: Number of results to return
        """
        self.neo4j_client = neo4j_client
        self.workspace_id = workspace_id or "default"
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.top_k = top_k
        
        self.logger = get_logger(
            "core_engine.reasoning.hybrid_retriever",
            workspace_id=self.workspace_id,
        )
        
        # Initialize Qdrant client
        load_env()
        qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        
        if QdrantClient is None:
            self.logger.warning("qdrant_client_not_available")
            self.qdrant_client = None
        else:
            try:
                self.qdrant_client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key,
                )
                self.qdrant_collection = qdrant_collection
                self.logger.info("qdrant_client_initialized")
            except Exception as e:
                self.logger.warning(
                    "qdrant_client_init_failed",
                    extra={"context": {"error": str(e)}},
                )
                self.qdrant_client = None
        
        # Initialize OpenAI for embeddings
        api_key = os.getenv("OPENAI_API_KEY")
        if OpenAI is None or not api_key:
            self.openai_client = None
            self.logger.warning("openai_client_not_available")
        else:
            self.openai_client = OpenAI(api_key=api_key)
            self.embed_model = embed_model
        # Initialize embedding cache
        self.embedding_cache = get_embedding_cache()
        
        # Initialize Query Expander (lazy loaded or initialized here)
        self.query_expander = QueryExpander(
            openai_client=self.openai_client,
            max_variations=3,
        )
        
    def retrieve(
        self,
        query: str,
        use_vector: bool = True,
        use_graph: bool = True,
        query_type: str = None,  # NEW: Allow passing query type for adaptive weights
    ) -> List[Dict[str, Any]]:
        """
        Retrieve results using hybrid approach.

        Args:
            query: Search query
            use_vector: Whether to use vector search
            use_graph: Whether to use graph search
            query_type: Optional query type for adaptive weights (entity_centric, multi_hop, etc.)

        Returns:
            List of retrieved results with scores
        """
        # OPTIMIZATION: Adaptive weights based on query type
        vector_weight, graph_weight = self._get_adaptive_weights(query, query_type)
        
        # PROACTIVE OPTIMIZATION: Pre-retrieval query expansion
        # Generate variations to improve vector search recall
        variations = [query]
        if use_vector:  # Only expand for vector search
            try:
                # Use query expander to get synonyms/variations
                variations = self.query_expander.expand(
                    query, 
                    context={"query_type": query_type or "general"}
                )
            except Exception as e:
                self.logger.warning(f"Query expansion failed: {e}")
                variations = [query]
        
        vector_results = []
        graph_results = []
        
        # Vector search - Run for ALL variations to maximize recall
        if use_vector and self.qdrant_client and self.openai_client:
            seen_texts = set()
            for variation in variations:
                try:
                    # Apply expansion weight penalty (original=1.0, variations=0.9)
                    # This ensures exact matches to original query are ranked higher
                    var_weight = vector_weight if variation == query else vector_weight * 0.9
                    
                    results = self._vector_search(variation, weight=var_weight)
                    
                    # Deduplicate results across variations
                    for res in results:
                        text_key = res.get("text", "")[:50].lower()
                        if text_key not in seen_texts:
                            seen_texts.add(text_key)
                            vector_results.append(res)
                            
                except Exception as e:
                    self.logger.warning(
                        "vector_search_failed",
                        extra={"context": {"error": str(e), "variation": variation}},
                    )
        
        # Graph search - Run ONLY for original query (precision + performance)
        # Graph already handles aliases/fuzzy matching better
        if use_graph:
            try:
                graph_results = self._graph_search(query, weight=graph_weight)
            except Exception as e:
                self.logger.warning(
                    "graph_search_failed",
                    extra={"context": {"error": str(e)}},
                )
        
        # Fuse results
        fused = self._fuse_results(vector_results, graph_results)
        
        # Improve diversity: ensure we get results from different episodes/sources
        diverse_results = self._diversify_results(fused)
        
        return diverse_results[:self.top_k]
    
    def _get_adaptive_weights(self, query: str, query_type: str = None) -> tuple:
        """
        Compute adaptive weights for RAG vs KG based on query characteristics.
        
        Strategy:
        - Entity queries (who is X, tell me about X) → More KG (0.3, 0.7)
        - Relationship queries (how does X relate to Y) → More KG (0.3, 0.7)
        - Concept queries (what is X, explain X) → More RAG (0.7, 0.3)
        - Multi-hop queries → Balanced (0.5, 0.5)
        - Default → Balanced (0.5, 0.5)
        
        Returns:
            Tuple of (vector_weight, graph_weight)
        """
        import re
        query_lower = query.lower().strip()
        
        # Pattern detection for entity-focused queries (favor KG)
        entity_patterns = [
            r"^who (is|are|was|were)",
            r"^tell me about ",
            r"^what did .+ say",
            r"^what does .+ think",
            r"^(what|who) (is|are) .+('s|s') ",  # possessives
        ]
        
        # Pattern detection for relationship queries (favor KG)
        relationship_patterns = [
            r"(relate|relationship|connect|between).*(and|to|with)",
            r"how (does|do|did).+affect",
            r"what (leads?|lead) to",
            r"(cause|effect|impact|influence)",
        ]
        
        # Pattern detection for concept queries (favor RAG)
        concept_patterns = [
            r"^what (is|are) ",
            r"^explain ",
            r"^describe ",
            r"^(how|why) (does|do|is|are) ",
        ]
        
        # Check query type if provided
        if query_type:
            if query_type in ["entity_centric", "entity_linking"]:
                return (0.35, 0.65)  # Favor KG
            elif query_type == "multi_hop":
                return (0.4, 0.6)  # Slightly favor KG
            elif query_type == "cross_episode":
                return (0.5, 0.5)  # Balanced
        
        # Pattern-based detection
        for pattern in entity_patterns:
            if re.search(pattern, query_lower):
                self.logger.info(
                    "adaptive_weights_entity",
                    extra={"context": {"query": query[:30], "weights": "(0.35, 0.65)"}}
                )
                return (0.35, 0.65)  # Favor KG
        
        for pattern in relationship_patterns:
            if re.search(pattern, query_lower):
                self.logger.info(
                    "adaptive_weights_relationship",
                    extra={"context": {"query": query[:30], "weights": "(0.35, 0.65)"}}
                )
                return (0.35, 0.65)  # Favor KG
        
        for pattern in concept_patterns:
            if re.search(pattern, query_lower):
                self.logger.info(
                    "adaptive_weights_concept",
                    extra={"context": {"query": query[:30], "weights": "(0.65, 0.35)"}}
                )
                return (0.65, 0.35)  # Favor RAG
        
        # Default: balanced
        return (self.vector_weight, self.graph_weight)

    def _vector_search(self, query: str, weight: float = None) -> List[Dict[str, Any]]:
        """
        Search using vector similarity.

        Args:
            query: Search query
            weight: Weight to apply to results (default: self.vector_weight)

        Returns:
            List of vector search results
        """
        weight = weight if weight is not None else self.vector_weight
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            if self.qdrant_collection not in collection_names:
                self.logger.warning(
                    "qdrant_collection_not_found",
                    extra={"context": {
                        "collection": self.qdrant_collection,
                        "available": collection_names
                    }}
                )
                return []
            
            # Create embedding (with caching)
            query_embedding = self.embedding_cache.get(query)
            
            if query_embedding is None:
                # Cache miss - generate embedding
                response = self.openai_client.embeddings.create(
                    model=self.embed_model,
                    input=[query],
                )
                query_embedding = response.data[0].embedding
                self.embedding_cache.set(query, query_embedding)
            
            # Search Qdrant - use query_points or query_batch depending on version
            try:
                # Try query_points first (newer API)
                if hasattr(self.qdrant_client, 'query_points'):
                    from qdrant_client.models import Filter, FieldCondition, MatchValue
                    try:
                        # Try with workspace filter
                        query_filter = Filter(
                            must=[
                                FieldCondition(
                                    key="workspace_id",
                                    match=MatchValue(value=self.workspace_id)
                                )
                            ]
                        )
                        response = self.qdrant_client.query_points(
                            collection_name=self.qdrant_collection,
                            query=query_embedding,
                            limit=self.top_k * 2,
                            query_filter=query_filter,
                        )
                        points = response.points
                    except Exception:
                        # Fallback without filter
                        response = self.qdrant_client.query_points(
                            collection_name=self.qdrant_collection,
                            query=query_embedding,
                            limit=self.top_k * 2,
                        )
                        points = response.points
                elif hasattr(self.qdrant_client, 'query_batch'):
                    # Alternative API
                    response = self.qdrant_client.query_batch(
                        collection_name=self.qdrant_collection,
                        queries=[query_embedding],
                        limit=self.top_k * 2,
                    )
                    points = response[0].points if response else []
                else:
                    # Fallback: try direct search method (older API)
                    points = self.qdrant_client.search(
                        collection_name=self.qdrant_collection,
                        query_vector=query_embedding,
                        limit=self.top_k * 2,
                    )
            except Exception as e:
                self.logger.error(
                    "qdrant_search_method_error",
                    extra={"context": {"error": str(e), "available_methods": [m for m in dir(self.qdrant_client) if not m.startswith('_')][:10]}}
                )
                return []
            
            vector_results = []
            for point in points:
                # Handle different point formats
                if hasattr(point, 'payload'):
                    payload = point.payload
                    score = getattr(point, 'score', 0.0)
                elif isinstance(point, dict):
                    payload = point.get('payload', {})
                    score = point.get('score', 0.0)
                else:
                    continue
                    
                # Add explanation
                payload["match_reason"] = "Semantic similarity match (Vector Search)"
                
                vector_results.append({
                    "text": payload.get("text", ""),
                    "source": "vector",
                    "score": score * weight,
                    "metadata": payload,
                })
            
            return vector_results
        except Exception as e:
            self.logger.error(
                "vector_search_error",
                exc_info=True,
                extra={"context": {"error": str(e), "query": query[:50]}}
            )
            raise

    def _graph_search(self, query: str, weight: float = None) -> List[Dict[str, Any]]:
        """
        Search using graph traversal with relationships.

        Args:
            query: Search query
            weight: Weight to apply to results (default: self.graph_weight)

        Returns:
            List of graph search results
        """
        weight = weight if weight is not None else self.graph_weight
        # Enhanced graph search - find concepts AND their relationships
        # Extract keywords from query
        import re
        stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why", "does", "do", "did", "this", "that"}
        keywords = [w.lower() for w in re.findall(r'\b\w+\b', query) 
                   if w.lower() not in stop_words and len(w) > 2]
        
        # If no keywords after filtering (e.g., "What is this?"), try broader search
        if not keywords:
            # Try to find any concepts - return top concepts if query is too vague
            keywords = [query.lower().strip("?.,!").strip()]
            # If still empty or just stop words, return empty (query too vague)
            if not keywords or keywords[0] in stop_words or len(keywords[0]) < 3:
                self.logger.warning(
                    "graph_search_too_vague",
                    extra={"context": {"query": query, "message": "Query too vague for graph search"}}
                )
                return []
        
        # Search for concepts matching keywords, including their relationships
        cypher = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (
            ANY(keyword IN $keywords WHERE toLower(c.name) CONTAINS keyword)
            OR ANY(keyword IN $keywords WHERE toLower(c.description) CONTAINS keyword)
          )
        OPTIONAL MATCH (c)-[r]->(related)
        WHERE related.workspace_id = $workspace_id
        OPTIONAL MATCH (related_to)-[r2]->(c)
        WHERE related_to.workspace_id = $workspace_id
        WITH c, 
             collect(DISTINCT {rel: type(r), target: related.name, desc: r.description})[0..5] as out_rels,
             collect(DISTINCT {rel: type(r2), source: related_to.name, desc: r2.description})[0..5] as in_rels
        RETURN 
            c.name as name,
            c.type as type,
            c.description as description,
            c.episode_ids as episode_ids,
            c.id as id,
            out_rels as relationships_out,
            in_rels as relationships_in
        LIMIT $limit
        """
        
        results = self.neo4j_client.execute_read(
            cypher,
            {
                "workspace_id": self.workspace_id,
                "keywords": keywords[:5],  # Use top 5 keywords
                "limit": self.top_k * 2,
            },
        )
        
        graph_results = []
        for result in results:
            # Calculate relevance score based on match quality
            name_lower = result.get("name", "").lower()
            desc_lower = result.get("description", "").lower()
            
            # Higher score for exact matches, lower for partial
            score = 0.0
            for keyword in keywords:
                if keyword in name_lower:
                    score += 1.0
                elif keyword in desc_lower:
                    score += 0.5
            
            # Boost score if has relationships (more connected = more relevant)
            rel_count = len(result.get("relationships_out", [])) + len(result.get("relationships_in", []))
            score += rel_count * 0.2
            
            if score > 0:
                # Build text representation with relationships
                text_parts = [f"{result.get('name', '')}: {result.get('description', '')}"]
                
                # Add relationship info
                if result.get("relationships_out"):
                    rels_text = ", ".join([f"{r.get('rel')} → {r.get('target')}" 
                                          for r in result.get("relationships_out", [])[:3]])
                    text_parts.append(f"Relationships: {rels_text}")
                
                # Add explanation
                match_reason = "Keyword match in Graph"
                if score > 1.0:
                    match_reason = "Strong Entity Match in Knowledge Graph"
                elif rel_count > 0:
                    match_reason = f"Concept Match with {rel_count} Relationships"
                
                graph_results.append({
                    "text": " | ".join(text_parts),
                    "source": "graph",
                    "score": score * weight,
                    "metadata": {
                        "name": result.get("name"),
                        "type": result.get("type"),
                        "description": result.get("description"),
                        "episode_ids": result.get("episode_ids", []),
                        "id": result.get("id"),
                        "relationships_out": result.get("relationships_out", []),
                        "relationships_in": result.get("relationships_in", []),
                        "match_reason": match_reason,  # Add explanation
                    },
                })
        
        return graph_results

    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Fuse vector and graph results.

        Args:
            vector_results: Vector search results
            graph_results: Graph search results

        Returns:
            Fused and ranked results
        """
        # Combine results
        all_results = {}
        
        for result in vector_results:
            key = result.get("text", "")[:100]  # Use text as key
            if key not in all_results:
                all_results[key] = result.copy()
            else:
                # Merge scores
                all_results[key]["score"] += result["score"]
                all_results[key]["sources"] = all_results[key].get("sources", []) + [result["source"]]
        
        for result in graph_results:
            key = result.get("text", "")[:100]
            if key not in all_results:
                all_results[key] = result.copy()
            else:
                all_results[key]["score"] += result["score"]
                all_results[key]["sources"] = all_results[key].get("sources", []) + [result["source"]]
        
        # Sort by score
        fused = sorted(all_results.values(), key=lambda x: x.get("score", 0), reverse=True)
        
        return fused
    
    def _diversify_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Improve result diversity by ensuring results from different episodes/sources.
        
        Args:
            results: List of results sorted by score
            
        Returns:
            Diversified results
        """
        if not results:
            return results
        
        # Group by episode/source
        seen_episodes = set()
        diverse = []
        remaining = []
        
        for result in results:
            metadata = result.get("metadata", {})
            episode_id = metadata.get("episode_id") or metadata.get("episode_ids", [])
            
            # Handle list of episode_ids
            if isinstance(episode_id, list) and episode_id:
                episode_id = episode_id[0]
            
            if episode_id and episode_id not in seen_episodes:
                diverse.append(result)
                seen_episodes.add(episode_id)
            else:
                remaining.append(result)
        
        # Add remaining results (from same episodes, but still valuable)
        # Limit to top results to maintain quality
        diverse.extend(remaining[:self.top_k - len(diverse)])
        
        return diverse

    def close(self) -> None:
        """Close connections."""
        if self.qdrant_client:
            # Qdrant client doesn't need explicit close
            pass
        self.logger.info("hybrid_retriever_closed")

