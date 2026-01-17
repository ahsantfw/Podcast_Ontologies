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
            self.logger.info("openai_client_initialized")

    def retrieve(
        self,
        query: str,
        use_vector: bool = True,
        use_graph: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve results using hybrid approach.

        Args:
            query: Search query
            use_vector: Whether to use vector search
            use_graph: Whether to use graph search

        Returns:
            List of retrieved results with scores
        """
        vector_results = []
        graph_results = []
        
        # Vector search
        if use_vector and self.qdrant_client and self.openai_client:
            try:
                vector_results = self._vector_search(query)
            except Exception as e:
                self.logger.warning(
                    "vector_search_failed",
                    extra={"context": {"error": str(e)}},
                )
        
        # Graph search
        if use_graph:
            try:
                graph_results = self._graph_search(query)
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

    def _vector_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search using vector similarity.

        Args:
            query: Search query

        Returns:
            List of vector search results
        """
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
            
            # Create embedding
            response = self.openai_client.embeddings.create(
                model=self.embed_model,
                input=[query],
            )
            query_embedding = response.data[0].embedding
            
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
                    
                vector_results.append({
                    "text": payload.get("text", ""),
                    "source": "vector",
                    "score": score * self.vector_weight,
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

    def _graph_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search using graph traversal with relationships.

        Args:
            query: Search query

        Returns:
            List of graph search results
        """
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
                
                graph_results.append({
                    "text": " | ".join(text_parts),
                    "source": "graph",
                    "score": score * self.graph_weight,
                    "metadata": {
                        "name": result.get("name"),
                        "type": result.get("type"),
                        "description": result.get("description"),
                        "episode_ids": result.get("episode_ids", []),
                        "id": result.get("id"),
                        "relationships_out": result.get("relationships_out", []),
                        "relationships_in": result.get("relationships_in", []),
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

