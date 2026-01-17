"""
JSON schemas for structured LLM extraction output.
Defines the expected structure for concept, relationship, and quote extraction.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

# JSON Schema for extraction output
EXTRACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier (normalized name)"},
                    "name": {"type": "string", "description": "Concept name as it appears"},
                    "type": {
                        "type": "string",
                        "enum": [
                            "Concept",
                            "Practice",
                            "CognitiveState",
                            "BehavioralPattern",
                            "Principle",
                            "Outcome",
                            "Causality",
                            "Person",
                            "Place",
                            "Organization",
                            "Event",
                        ],
                        "description": "Concept type",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description or definition",
                    },
                    "text_span": {
                        "type": "string",
                        "description": "Exact text from transcript where concept is mentioned",
                    },
                    "start_char": {"type": "integer", "description": "Start character offset"},
                    "end_char": {"type": "integer", "description": "End character offset"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score (0-1)",
                    },
                },
                "required": ["id", "name", "type", "text_span", "confidence"],
            },
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Source concept ID",
                    },
                    "target_id": {
                        "type": "string",
                        "description": "Target concept ID",
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "CAUSES",
                            "INFLUENCES",
                            "OPTIMIZES",
                            "ENABLES",
                            "REDUCES",
                            "LEADS_TO",
                            "REQUIRES",
                            "RELATES_TO",
                            "IS_PART_OF",
                        ],
                        "description": "Relationship type",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the relationship",
                    },
                    "text_span": {
                        "type": "string",
                        "description": "Exact text from transcript describing the relationship",
                    },
                    "start_char": {"type": "integer"},
                    "end_char": {"type": "integer"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
                "required": ["source_id", "target_id", "type", "confidence"],
            },
        },
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Exact quote text",
                    },
                    "speaker": {
                        "type": "string",
                        "description": "Speaker name (if mentioned)",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "Timestamp (if available)",
                    },
                    "related_concepts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Concept IDs this quote relates to",
                    },
                    "start_char": {"type": "integer"},
                    "end_char": {"type": "integer"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
                "required": ["text", "confidence"],
            },
        },
    },
    "required": ["concepts", "relationships", "quotes"],
}


def validate_extraction_output(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate extraction output against schema.

    Args:
        data: Extracted data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Output must be a dictionary"

    required_keys = ["concepts", "relationships", "quotes"]
    for key in required_keys:
        if key not in data:
            return False, f"Missing required key: {key}"
        if not isinstance(data[key], list):
            return False, f"{key} must be a list"

    # Validate concepts
    for i, concept in enumerate(data["concepts"]):
        if not isinstance(concept, dict):
            return False, f"concepts[{i}] must be a dictionary"
        required = ["id", "name", "type", "text_span", "confidence"]
        for req in required:
            if req not in concept:
                return False, f"concepts[{i}] missing required field: {req}"

    # Validate relationships
    for i, rel in enumerate(data["relationships"]):
        if not isinstance(rel, dict):
            return False, f"relationships[{i}] must be a dictionary"
        required = ["source_id", "target_id", "type", "confidence"]
        for req in required:
            if req not in rel:
                return False, f"relationships[{i}] missing required field: {req}"

    # Validate quotes
    for i, quote in enumerate(data["quotes"]):
        if not isinstance(quote, dict):
            return False, f"quotes[{i}] must be a dictionary"
        if "text" not in quote:
            return False, f"quotes[{i}] missing required field: text"

    return True, None

