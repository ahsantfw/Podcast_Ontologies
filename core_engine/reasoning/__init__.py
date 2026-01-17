"""
Reasoning module for querying and reasoning over the knowledge graph.
Provides natural language query interface, hybrid RAG + KG retrieval,
multi-hop reasoning, and agent interfaces with session management.

ENHANCED with Intent Classification Engine for intelligent query understanding.
"""

from core_engine.reasoning.query_generator import QueryGenerator
from core_engine.reasoning.cypher_chain import KGCypherChain
from core_engine.reasoning.hybrid_retriever import HybridRetriever
from core_engine.reasoning.multi_hop import MultiHopReasoner
from core_engine.reasoning.session_manager import SessionManager, QuerySession
from core_engine.reasoning.agent_tools import KGTools, create_kg_tools
from core_engine.reasoning.query_templates import QueryTemplates
from core_engine.reasoning.reasoning import KGReasoner, create_reasoner
from core_engine.reasoning.intent_classifier import IntentClassifier, QueryIntent

__all__ = [
    "QueryGenerator",
    "KGCypherChain",
    "HybridRetriever",
    "MultiHopReasoner",
    "SessionManager",
    "QuerySession",
    "KGTools",
    "create_kg_tools",
    "QueryTemplates",
    "KGReasoner",
    "create_reasoner",
    "IntentClassifier",
    "QueryIntent",
]

