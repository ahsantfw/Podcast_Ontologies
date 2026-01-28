"""
LangGraph State Definition for Retrieval Workflow

This module defines the state that flows through the LangGraph workflow.
"""
from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class QueryPlan:
    """Query plan from intelligent planner."""
    is_follow_up: bool = False
    is_relevant: bool = True
    complexity: str = "simple"  # "simple", "moderate", "complex"
    intent: str = "knowledge_query"
    needs_decomposition: bool = False
    sub_queries: List[str] = None
    entities: List[str] = None
    retrieval_strategy: Dict[str, Any] = None
    rejection_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.sub_queries is None:
            self.sub_queries = []
        if self.entities is None:
            self.entities = []
        if self.retrieval_strategy is None:
            self.retrieval_strategy = {
                "use_rag": True,
                "use_kg": True,
                "kg_query_type": "entity_centric",
                "rag_expansion": False,
                "iterative": False,
            }


class RetrievalState(TypedDict):
    """State passed through LangGraph workflow."""
    # Input
    query: str
    conversation_history: List[Dict[str, Any]]
    session_metadata: Dict[str, Any]
    
    # Planning
    query_plan: Optional[QueryPlan]
    
    # Retrieval
    rag_results: List[Dict[str, Any]]
    kg_results: List[Dict[str, Any]]
    
    # Processing
    reranked_results: List[Dict[str, Any]]
    
    # Output
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    # Control flow
    should_continue: bool
    error: Optional[str]
    
    # Component references (passed through, not serialized)
    hybrid_retriever: Any  # HybridRetriever instance
    neo4j_client: Any  # Neo4jClient instance
    podcast_agent: Any  # PodcastAgent instance
    openai_client: Any  # OpenAI client instance
