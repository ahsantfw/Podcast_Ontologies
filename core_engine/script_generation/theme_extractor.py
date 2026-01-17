"""
Theme Extractor - Extract themes, concepts, and quotes related to a topic.
"""

from typing import List, Dict, Any, Optional
from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.logging import get_logger

logger = get_logger(__name__)


class ThemeExtractor:
    """Extract themes, concepts, quotes, and relationships from Knowledge Graph."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.client = get_neo4j_client(workspace_id)
    
    def extract_theme_content(
        self,
        theme: str,
        episodes: Optional[List[str]] = None,
        max_concepts: int = 50,
        max_quotes: int = 30
    ) -> Dict[str, Any]:
        """
        Extract all content related to a theme.
        
        Args:
            theme: Theme/topic to extract (e.g., "creativity", "discipline")
            episodes: Optional list of episode IDs to filter by
            max_concepts: Maximum concepts to return
            max_quotes: Maximum quotes to return
            
        Returns:
            Dictionary with:
            - concepts: List of related concepts
            - quotes: List of related quotes
            - relationships: List of relationships
            - cross_episode_patterns: Concepts appearing in multiple episodes
        """
        logger.info("extracting_theme", extra={"theme": theme, "workspace_id": self.workspace_id})
        
        # Extract concepts related to theme
        concepts = self._extract_theme_concepts(theme, episodes, max_concepts)
        
        # Extract quotes related to theme
        quotes = self._extract_theme_quotes(theme, episodes, max_quotes)
        
        # Extract relationships
        relationships = self._extract_theme_relationships(theme, episodes)
        
        # Find cross-episode patterns
        cross_episode_patterns = self._find_cross_episode_patterns(theme, episodes)
        
        return {
            "theme": theme,
            "concepts": concepts,
            "quotes": quotes,
            "relationships": relationships,
            "cross_episode_patterns": cross_episode_patterns,
            "total_concepts": len(concepts),
            "total_quotes": len(quotes),
        }
    
    def _extract_theme_concepts(
        self,
        theme: str,
        episodes: Optional[List[str]] = None,
        max_concepts: int = 50
    ) -> List[Dict[str, Any]]:
        """Extract concepts related to theme."""
        query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (
            toLower(c.name) CONTAINS toLower($theme)
            OR toLower(c.description) CONTAINS toLower($theme)
          )
        """
        
        if episodes:
            query += """
              AND c.episode_ids IS NOT NULL
              AND ANY(ep IN $episodes WHERE ep IN c.episode_ids)
            """
        
        query += """
        RETURN c.id as id,
               c.name as name,
               c.type as type,
               c.description as description,
               c.episode_ids as episode_ids,
               c.source_paths as source_paths,
               size(c.episode_ids) as episode_count
        ORDER BY episode_count DESC, c.name
        LIMIT $max_concepts
        """
        
        params = {
            "workspace_id": self.workspace_id,
            "theme": theme,
            "max_concepts": max_concepts
        }
        
        if episodes:
            params["episodes"] = episodes
        
        try:
            results = self.client.execute_read(query, params)
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("extract_concepts_failed", exc_info=True, extra={"error": str(e)})
            return []
    
    def _extract_theme_quotes(
        self,
        theme: str,
        episodes: Optional[List[str]] = None,
        max_quotes: int = 30
    ) -> List[Dict[str, Any]]:
        """Extract quotes related to theme using multiple strategies."""
        quotes = []
        
        # Strategy 1: Find quotes directly by text match
        query1 = """
        MATCH (q:Quote)
        WHERE q.workspace_id = $workspace_id
          AND toLower(q.text) CONTAINS toLower($theme)
        """
        
        if episodes:
            query1 += " AND q.episode_id IN $episodes"
        
        query1 += """
        RETURN q.id as id,
               q.text as text,
               q.speaker as speaker,
               q.timestamp as timestamp,
               q.episode_id as episode_id,
               q.source_path as source_path,
               q.start_char as start_char,
               q.end_char as end_char,
               'direct_match' as source
        LIMIT $max_quotes
        """
        
        params1 = {
            "workspace_id": self.workspace_id,
            "theme": theme,
            "max_quotes": max_quotes
        }
        if episodes:
            params1["episodes"] = episodes
        
        try:
            results1 = self.client.execute_read(query1, params1)
            quotes.extend([dict(r) for r in results1])
            logger.info("found_quotes_direct", extra={"count": len(quotes)})
        except Exception as e:
            logger.warning("direct_quote_search_failed", extra={"error": str(e)})
        
        # Strategy 2: Find quotes via concept relationships (ABOUT relationship)
        concept_query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (
            toLower(c.name) CONTAINS toLower($theme)
            OR toLower(c.description) CONTAINS toLower($theme)
          )
        RETURN c.id as concept_id, c.name as concept_name
        LIMIT 20
        """
        
        try:
            concept_results = self.client.execute_read(
                concept_query,
                {"workspace_id": self.workspace_id, "theme": theme}
            )
            concept_ids = [r["concept_id"] for r in concept_results]
            
            if concept_ids:
                query2 = """
                MATCH (q:Quote)-[r:ABOUT]->(c)
                WHERE q.workspace_id = $workspace_id
                  AND c.id IN $concept_ids
                """
                
                if episodes:
                    query2 += " AND q.episode_id IN $episodes"
                
                query2 += """
                RETURN DISTINCT q.id as id,
                       q.text as text,
                       q.speaker as speaker,
                       q.timestamp as timestamp,
                       q.episode_id as episode_id,
                       q.source_path as source_path,
                       q.start_char as start_char,
                       q.end_char as end_char,
                       c.name as related_concept,
                       'concept_link' as source
                ORDER BY q.timestamp
                LIMIT $max_quotes
                """
                
                params2 = {
                    "workspace_id": self.workspace_id,
                    "concept_ids": concept_ids,
                    "max_quotes": max_quotes
                }
                if episodes:
                    params2["episodes"] = episodes
                
                try:
                    results2 = self.client.execute_read(query2, params2)
                    for r in results2:
                        quote_dict = dict(r)
                        # Avoid duplicates
                        if not any(q.get("id") == quote_dict.get("id") for q in quotes):
                            quotes.append(quote_dict)
                    logger.info("found_quotes_via_concepts", extra={"count": len(results2)})
                except Exception as e:
                    logger.warning("concept_linked_quote_search_failed", extra={"error": str(e)})
        except Exception as e:
            logger.warning("concept_search_failed", extra={"error": str(e)})
        
        # Strategy 3: Extract quotes from relationship text_spans (using array indexing)
        if len(quotes) < max_quotes:
            try:
                rel_query = """
                MATCH (c1)-[r]->(c2)
                WHERE c1.workspace_id = $workspace_id
                  AND c2.workspace_id = $workspace_id
                  AND (
                    toLower(c1.name) CONTAINS toLower($theme)
                    OR toLower(c2.name) CONTAINS toLower($theme)
                    OR toLower(c1.description) CONTAINS toLower($theme)
                    OR toLower(c2.description) CONTAINS toLower($theme)
                  )
                  AND r.text_spans IS NOT NULL
                  AND size(r.text_spans) > 0
                RETURN r.text_spans as text_spans,
                       r.timestamps as timestamps,
                       r.source_paths as source_paths,
                       r.episode_ids as episode_ids,
                       r.speakers as speakers,
                       r.start_chars as start_chars,
                       r.end_chars as end_chars,
                       c1.episode_ids as c1_episodes,
                       c2.episode_ids as c2_episodes,
                       c1.source_paths as c1_sources,
                       c2.source_paths as c2_sources
                LIMIT 50
                """
                
                rel_params = {"workspace_id": self.workspace_id, "theme": theme}
                
                rel_results = self.client.execute_read(rel_query, rel_params)
                
                for rel_record in rel_results:
                    text_spans = rel_record.get("text_spans") or []
                    timestamps = rel_record.get("timestamps") or []
                    source_paths = rel_record.get("source_paths") or []
                    episode_ids = rel_record.get("episode_ids") or []
                    speakers = rel_record.get("speakers") or []
                    start_chars = rel_record.get("start_chars") or []
                    end_chars = rel_record.get("end_chars") or []
                    
                    # Use concept episodes/sources as fallback
                    c1_episodes = rel_record.get("c1_episodes") or []
                    c2_episodes = rel_record.get("c2_episodes") or []
                    fallback_episode_ids = episode_ids if episode_ids else (c1_episodes if c1_episodes else c2_episodes)
                    
                    c1_sources = rel_record.get("c1_sources") or []
                    c2_sources = rel_record.get("c2_sources") or []
                    fallback_sources = source_paths if source_paths else (c1_sources if c1_sources else c2_sources)
                    
                    for idx, quote_text in enumerate(text_spans):
                        if len(quotes) >= max_quotes:
                            break
                        if not quote_text or len(quote_text.strip()) < 20:
                            continue
                        if theme.lower() not in quote_text.lower():
                            continue
                        
                        # Filter by episodes if specified
                        ep_id = episode_ids[idx] if idx < len(episode_ids) else (fallback_episode_ids[0] if fallback_episode_ids else "")
                        if episodes and ep_id and ep_id not in episodes:
                            continue
                        
                        quote_dict = {
                            "id": f"rel_span_{ep_id}_{idx}_{hash(quote_text[:50]) % 10000}",
                            "text": quote_text.strip(),
                            "speaker": speakers[idx] if idx < len(speakers) else None,
                            "timestamp": timestamps[idx] if idx < len(timestamps) else None,
                            "episode_id": ep_id,
                            "source_path": source_paths[idx] if idx < len(source_paths) else (fallback_sources[0] if fallback_sources else ""),
                            "start_char": start_chars[idx] if idx < len(start_chars) else 0,
                            "end_char": end_chars[idx] if idx < len(end_chars) else 0,
                            "source": "relationship_span"
                        }
                        
                        # Avoid duplicates
                        if not any(q.get("text", "").strip() == quote_dict.get("text") and q.get("episode_id") == quote_dict.get("episode_id") for q in quotes):
                            quotes.append(quote_dict)
                    
                    if len(quotes) >= max_quotes:
                        break
                
                logger.info("found_quotes_from_relationships", extra={"count": len(quotes)})
            except Exception as e:
                logger.warning("relationship_quote_extraction_failed", exc_info=True, extra={"error": str(e)})
        
        # Strategy 4: Extract quotes from concept text_spans
        if len(quotes) < max_quotes:
            try:
                concept_span_query = """
                MATCH (c)
                WHERE c.workspace_id = $workspace_id
                  AND (
                    toLower(c.name) CONTAINS toLower($theme)
                    OR toLower(c.description) CONTAINS toLower($theme)
                  )
                  AND c.text_spans IS NOT NULL
                  AND size(c.text_spans) > 0
                """
                
                if episodes:
                    concept_span_query += """
                      AND c.episode_ids IS NOT NULL
                      AND ANY(ep IN $episodes WHERE ep IN c.episode_ids)
                    """
                
                concept_span_query += """
                RETURN c.text_spans as text_spans,
                       c.episode_ids as episode_ids,
                       c.source_paths as source_paths,
                       c.name as concept_name
                LIMIT 50
                """
                
                concept_span_params = {"workspace_id": self.workspace_id, "theme": theme}
                if episodes:
                    concept_span_params["episodes"] = episodes
                
                concept_span_results = self.client.execute_read(concept_span_query, concept_span_params)
                
                for record in concept_span_results:
                    text_spans = record.get("text_spans") or []
                    episode_ids = record.get("episode_ids") or []
                    source_paths = record.get("source_paths") or []
                    concept_name = record.get("concept_name", "")
                    
                    for idx, quote_text in enumerate(text_spans):
                        if len(quotes) >= max_quotes:
                            break
                        if not quote_text or len(quote_text.strip()) < 20:
                            continue
                        if theme.lower() not in quote_text.lower():
                            continue
                        
                        ep_id = episode_ids[idx] if idx < len(episode_ids) else (episode_ids[0] if episode_ids else "")
                        
                        quote_dict = {
                            "id": f"concept_span_{ep_id}_{idx}_{hash(quote_text[:50]) % 10000}",
                            "text": quote_text.strip(),
                            "speaker": None,
                            "timestamp": None,
                            "episode_id": ep_id,
                            "source_path": source_paths[idx] if idx < len(source_paths) else (source_paths[0] if source_paths else ""),
                            "start_char": 0,
                            "end_char": 0,
                            "source": "concept_span",
                            "related_concept": concept_name
                        }
                        
                        # Avoid duplicates
                        if not any(q.get("text", "").strip() == quote_dict.get("text") and q.get("episode_id") == quote_dict.get("episode_id") for q in quotes):
                            quotes.append(quote_dict)
                    
                    if len(quotes) >= max_quotes:
                        break
                
                logger.info("found_quotes_from_concept_spans", extra={"count": len(concept_span_results)})
            except Exception as e:
                logger.warning("concept_span_quote_extraction_failed", exc_info=True, extra={"error": str(e)})
        
        # Strategy 5: Use vector search as last resort (if Qdrant is available)
        if len(quotes) == 0:
            try:
                from core_engine.reasoning.hybrid_retriever import HybridRetriever
                retriever = HybridRetriever(self.workspace_id)
                # Search for relevant text chunks
                rag_results = retriever.retrieve(theme, top_k=min(max_quotes * 2, 20))
                
                for result in rag_results:
                    if len(quotes) >= max_quotes:
                        break
                    result_text = result.get("text", "")
                    if result_text and len(result_text.strip()) > 50:
                        # Extract quotes from RAG results
                        quote_dict = {
                            "id": f"rag_{hash(result_text[:100]) % 100000}",
                            "text": result_text.strip()[:500],  # Limit length
                            "speaker": result.get("metadata", {}).get("speaker"),
                            "timestamp": result.get("metadata", {}).get("timestamp"),
                            "episode_id": result.get("metadata", {}).get("episode_id", ""),
                            "source_path": result.get("metadata", {}).get("source_path", ""),
                            "start_char": result.get("metadata", {}).get("start_char", 0),
                            "end_char": result.get("metadata", {}).get("end_char", 0),
                            "source": "rag_fallback"
                        }
                        quotes.append(quote_dict)
                        
                logger.info("found_quotes_via_rag", extra={"count": len(quotes)})
            except Exception as e:
                logger.warning("rag_quote_fallback_failed", exc_info=True, extra={"error": str(e)})
        
        # Remove duplicates and limit
        seen = set()
        unique_quotes = []
        for quote in quotes:
            text_key = (quote.get("text", "").strip()[:100].lower(), quote.get("episode_id", ""))
            if text_key not in seen:
                seen.add(text_key)
                unique_quotes.append(quote)
            if len(unique_quotes) >= max_quotes:
                break
        
        logger.info("quote_extraction_complete", extra={
            "theme": theme,
            "total_found": len(unique_quotes),
            "strategies_used": len(set(q.get("source") for q in unique_quotes))
        })
        
        return unique_quotes
    
    def _extract_theme_relationships(
        self,
        theme: str,
        episodes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Extract relationships involving theme concepts."""
        query = """
        MATCH (c1)-[r]->(c2)
        WHERE c1.workspace_id = $workspace_id
          AND c2.workspace_id = $workspace_id
          AND (
            toLower(c1.name) CONTAINS toLower($theme)
            OR toLower(c2.name) CONTAINS toLower($theme)
            OR toLower(c1.description) CONTAINS toLower($theme)
            OR toLower(c2.description) CONTAINS toLower($theme)
          )
        """
        
        if episodes:
            query += """
              AND (
                (c1.episode_ids IS NOT NULL AND ANY(ep IN $episodes WHERE ep IN c1.episode_ids))
                OR (c2.episode_ids IS NOT NULL AND ANY(ep IN $episodes WHERE ep IN c2.episode_ids))
              )
            """
        
        query += """
        RETURN c1.name as source,
               type(r) as relationship,
               c2.name as target,
               r.description as description,
               c1.type as source_type,
               c2.type as target_type
        LIMIT 30
        """
        
        params = {
            "workspace_id": self.workspace_id,
            "theme": theme
        }
        
        if episodes:
            params["episodes"] = episodes
        
        try:
            results = self.client.execute_read(query, params)
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("extract_relationships_failed", exc_info=True, extra={"error": str(e)})
            return []
    
    def _find_cross_episode_patterns(
        self,
        theme: str,
        episodes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Find concepts that appear across multiple episodes."""
        query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (
            toLower(c.name) CONTAINS toLower($theme)
            OR toLower(c.description) CONTAINS toLower($theme)
          )
          AND c.episode_ids IS NOT NULL
          AND size(c.episode_ids) >= 2
        """
        
        if episodes:
            query += """
              AND ANY(ep IN $episodes WHERE ep IN c.episode_ids)
            """
        
        query += """
        RETURN c.id as id,
               c.name as name,
               c.type as type,
               c.description as description,
               c.episode_ids as episode_ids,
               size(c.episode_ids) as episode_count
        ORDER BY episode_count DESC
        LIMIT 20
        """
        
        params = {
            "workspace_id": self.workspace_id,
            "theme": theme
        }
        
        if episodes:
            params["episodes"] = episodes
        
        try:
            results = self.client.execute_read(query, params)
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("find_patterns_failed", exc_info=True, extra={"error": str(e)})
            return []
    
    def close(self):
        """Close Neo4j connection."""
        if self.client:
            self.client.close()
