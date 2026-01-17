"""
Entity normalization and deduplication.
Normalizes concept names and links to existing nodes in Neo4j.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional, List
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger


def normalize_concept_id(name: str) -> str:
    """
    Normalize concept name to ID.

    Args:
        name: Concept name

    Returns:
        Normalized ID (lowercase, no special chars, spaces to underscores)
    """
    # Lowercase
    normalized = name.lower().strip()
    
    # Replace spaces and special chars with underscores
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    normalized = re.sub(r'[\s_-]+', '_', normalized)
    
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    
    return normalized


def normalize_concept_name(name: str) -> str:
    """
    Normalize concept name (preserve capitalization for display).

    Args:
        name: Concept name

    Returns:
        Normalized name (trimmed, normalized whitespace)
    """
    # Trim and normalize whitespace
    normalized = ' '.join(name.split())
    return normalized


class EntityNormalizer:
    """Normalize and deduplicate entities."""

    def __init__(self, client: Neo4jClient, workspace_id: Optional[str] = None):
        """
        Initialize normalizer.

        Args:
            client: Neo4j client
            workspace_id: Workspace identifier
        """
        self.client = client
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger(
            "core_engine.kg.normalizer",
            workspace_id=self.workspace_id,
        )
        self._cache: Dict[str, Optional[str]] = {}  # Cache normalized_id -> existing_id

    def normalize_concept(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a concept.

        Args:
            concept: Concept dictionary

        Returns:
            Normalized concept with updated ID
        """
        name = concept.get("name", "")
        concept_type = concept.get("type", "Concept")
        
        # Generate normalized ID
        normalized_id = normalize_concept_id(name)
        
        # Check if concept already exists in Neo4j
        existing_id = self._find_existing_concept(normalized_id, concept_type)
        
        if existing_id:
            # Use existing ID
            concept["id"] = existing_id
            concept["is_existing"] = True
            self.logger.debug(
                "concept_linked",
                extra={
                    "context": {
                        "name": name,
                        "normalized_id": normalized_id,
                        "existing_id": existing_id,
                    }
                },
            )
        else:
            # Use normalized ID
            concept["id"] = normalized_id
            concept["is_existing"] = False
        
        # Normalize name
        concept["name"] = normalize_concept_name(name)
        
        return concept

    def normalize_relationship(
        self, relationship: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalize relationship source/target IDs.

        Args:
            relationship: Relationship dictionary

        Returns:
            Normalized relationship
        """
        source_id = relationship.get("source_id", "")
        target_id = relationship.get("target_id", "")
        
        # Normalize IDs
        relationship["source_id"] = normalize_concept_id(source_id)
        relationship["target_id"] = normalize_concept_id(target_id)
        
        return relationship

    def _find_existing_concept(
        self, normalized_id: str, concept_type: str
    ) -> Optional[str]:
        """
        Find existing concept in Neo4j by normalized ID.

        Args:
            normalized_id: Normalized concept ID
            concept_type: Concept type

        Returns:
            Existing concept ID if found, None otherwise
        """
        # Check cache first
        cache_key = f"{concept_type}:{normalized_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Query Neo4j
        # Map concept type to Neo4j label
        label_map = {
            "Concept": "Concept",
            "Practice": "Practice",
            "CognitiveState": "CognitiveState",
            "BehavioralPattern": "BehavioralPattern",
            "Principle": "Principle",
            "Outcome": "Outcome",
            "Causality": "Causality",
            "Person": "Person",
            "Place": "Place",
            "Organization": "Organization",
            "Event": "Event",
        }
        label = label_map.get(concept_type, "Concept")
        
        query = f"""
        MATCH (c:{label})
        WHERE c.id = $id AND c.workspace_id = $workspace_id
        RETURN c.id as id
        LIMIT 1
        """
        
        result = self.client.execute_read(
            query,
            {"id": normalized_id, "workspace_id": self.workspace_id},
        )
        
        existing_id = result[0]["id"] if result else None
        self._cache[cache_key] = existing_id
        
        return existing_id
    
    def _find_existing_concept_by_id(self, concept_id: str) -> Optional[str]:
        """
        Find existing concept in Neo4j by ID (any label).
        Used for relationship normalization when concepts aren't in current extraction.
        
        Args:
            concept_id: Concept ID to look up
            
        Returns:
            Existing concept ID if found, None otherwise
        """
        # Check cache first
        cache_key = f"any:{concept_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Query Neo4j - check all concept labels
        query = """
        MATCH (c)
        WHERE c.id = $id 
          AND c.workspace_id = $workspace_id
          AND (c:Concept OR c:Practice OR c:CognitiveState OR c:BehavioralPattern 
               OR c:Principle OR c:Outcome OR c:Causality OR c:Person 
               OR c:Place OR c:Organization OR c:Event)
        RETURN c.id as id
        LIMIT 1
        """
        
        result = self.client.execute_read(
            query,
            {"id": concept_id, "workspace_id": self.workspace_id},
        )
        
        existing_id = result[0]["id"] if result else None
        self._cache[cache_key] = existing_id
        return existing_id

    def normalize_extraction(
        self, extraction: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Normalize entire extraction result.

        Args:
            extraction: Extraction result with concepts, relationships, quotes

        Returns:
            Normalized extraction result
        """
        # Normalize concepts first
        normalized_concepts = [
            self.normalize_concept(c) for c in extraction.get("concepts", [])
        ]
        
        # Build a map from normalized_id -> actual_id (in case concepts were linked)
        # This ensures relationships reference the correct concept IDs
        concept_id_map = {}
        for concept in normalized_concepts:
            normalized_id = normalize_concept_id(concept.get("name", ""))
            actual_id = concept.get("id", normalized_id)
            concept_id_map[normalized_id] = actual_id
            # Also map by name in case relationships use names
            concept_name = concept.get("name", "")
            if concept_name:
                concept_id_map[concept_name.lower()] = actual_id
        
        # Normalize relationships and update IDs to match actual concept IDs
        normalized_relationships = []
        for r in extraction.get("relationships", []):
            normalized_rel = self.normalize_relationship(r)
            # Update source_id and target_id to use actual concept IDs
            source_id = normalized_rel.get("source_id", "")
            target_id = normalized_rel.get("target_id", "")
            
            # Look up actual IDs from concept map (current extraction)
            if source_id in concept_id_map:
                normalized_rel["source_id"] = concept_id_map[source_id]
            else:
                # Not in current extraction - check if it exists in database
                existing_source_id = self._find_existing_concept_by_id(source_id)
                if existing_source_id:
                    normalized_rel["source_id"] = existing_source_id
            
            if target_id in concept_id_map:
                normalized_rel["target_id"] = concept_id_map[target_id]
            else:
                # Not in current extraction - check if it exists in database
                existing_target_id = self._find_existing_concept_by_id(target_id)
                if existing_target_id:
                    normalized_rel["target_id"] = existing_target_id
            
            normalized_relationships.append(normalized_rel)
        
        # Quotes don't need normalization (just pass through)
        normalized_quotes = extraction.get("quotes", [])
        
        return {
            "concepts": normalized_concepts,
            "relationships": normalized_relationships,
            "quotes": normalized_quotes,
        }


def normalize_extraction(
    extraction: Dict[str, List[Dict[str, Any]]],
    client: Neo4jClient,
    workspace_id: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Normalize extraction result (convenience function).

    Args:
        extraction: Extraction result
        client: Neo4j client
        workspace_id: Workspace identifier

    Returns:
        Normalized extraction result
    """
    normalizer = EntityNormalizer(client, workspace_id=workspace_id)
    return normalizer.normalize_extraction(extraction)

