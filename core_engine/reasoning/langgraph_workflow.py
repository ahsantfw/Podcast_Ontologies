"""
LangGraph Workflow for Retrieval System

This workflow orchestrates the retrieval and synthesis process using LangGraph.
It wraps existing components to ensure backward compatibility.
"""
import os
from typing import Optional
from core_engine.logging import get_logger

logger = get_logger(__name__)

# Try to import LangGraph, but make it optional
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("langgraph_not_available", extra={"context": {"message": "LangGraph not installed. Install with: pip install langgraph"}})


def create_retrieval_workflow():
    """
    Create LangGraph workflow for retrieval.
    
    Returns:
        Compiled LangGraph workflow, or None if LangGraph not available
    """
    if not LANGGRAPH_AVAILABLE:
        logger.warning("langgraph_workflow_not_created", extra={"context": {"reason": "LangGraph not available"}})
        return None
    
    try:
        from core_engine.reasoning.langgraph_state import RetrievalState
        from core_engine.reasoning.langgraph_nodes import (
            plan_query_node,
            retrieve_rag_node,
            retrieve_kg_node,
            rerank_node,
            synthesize_node,
            self_reflect_node,
        )
        
        # Create workflow
        workflow = StateGraph(RetrievalState)
        
        # Add nodes
        workflow.add_node("plan_query", plan_query_node)
        workflow.add_node("retrieve_rag", retrieve_rag_node)
        workflow.add_node("retrieve_kg", retrieve_kg_node)
        workflow.add_node("rerank", rerank_node)
        workflow.add_node("synthesize", synthesize_node)
        workflow.add_node("self_reflect", self_reflect_node)  # Final quality check
        
        # Define edges
        workflow.set_entry_point("plan_query")
        
        # Route after planning (for now, always continue)
        def route_after_planning(state: RetrievalState) -> str:
            """Route after planning node."""
            if not state.get("should_continue", True):
                return END
            return "retrieve_rag"
        
        workflow.add_conditional_edges(
            "plan_query",
            route_after_planning,
            {
                END: END,
                "retrieve_rag": "retrieve_rag",
            }
        )
        
        # Route after KG retrieval (check if should_continue was set to False)
        def route_after_kg(state: RetrievalState) -> str:
            """Route after KG retrieval - check if synthesis should be blocked."""
            if not state.get("should_continue", True):
                return END
            return "rerank"
        
        # Parallel retrieval (RAG then KG)
        workflow.add_edge("retrieve_rag", "retrieve_kg")
        
        # Add conditional edge after KG to check if synthesis should be blocked
        workflow.add_conditional_edges(
            "retrieve_kg",
            route_after_kg,
            {
                END: END,
                "rerank": "rerank",
            }
        )
        
        workflow.add_edge("rerank", "synthesize")
        workflow.add_edge("synthesize", "self_reflect")
        
        # Route after self-reflection (final check)
        def route_after_reflection(state: RetrievalState) -> str:
            """Route after self-reflection - final gate."""
            if not state.get("should_continue", True):
                return END
            return END  # Always end after reflection
        
        workflow.add_conditional_edges(
            "self_reflect",
            route_after_reflection,
            {
                END: END,
            }
        )
        
        # Compile workflow
        compiled = workflow.compile()
        
        logger.info("langgraph_workflow_created")
        return compiled
        
    except Exception as e:
        logger.error(
            "langgraph_workflow_creation_failed",
            exc_info=True,
            extra={"context": {"error": str(e)}}
        )
        return None


def run_workflow_simple(
    workflow,
    query: str,
    conversation_history: list,
    session_metadata: dict,
    hybrid_retriever,
    neo4j_client,
    podcast_agent,
    openai_client,
) -> dict:
    """
    Run workflow with simple state preparation.
    
    Args:
        workflow: Compiled LangGraph workflow
        query: User query
        conversation_history: Conversation history
        session_metadata: Session metadata
        hybrid_retriever: HybridRetriever instance
        neo4j_client: Neo4jClient instance
        podcast_agent: PodcastAgent instance
        openai_client: OpenAI client instance
    
    Returns:
        Final state dictionary
    """
    if not workflow:
        raise ValueError("Workflow not available")
    
    # Prepare initial state
    initial_state: RetrievalState = {
        "query": query,
        "conversation_history": conversation_history,
        "session_metadata": session_metadata,
        "query_plan": None,
        "rag_results": [],
        "kg_results": [],
        "reranked_results": [],
        "answer": "",
        "sources": [],
        "metadata": {},
        "should_continue": True,
        "error": None,
        "hybrid_retriever": hybrid_retriever,
        "neo4j_client": neo4j_client,
        "podcast_agent": podcast_agent,
        "openai_client": openai_client,
    }
    
    # Run workflow
    try:
        final_state = workflow.invoke(initial_state)
        return final_state
    except Exception as e:
        logger.error(
            "langgraph_workflow_execution_failed",
            exc_info=True,
            extra={"context": {"query": query[:50], "error": str(e)}}
        )
        raise
