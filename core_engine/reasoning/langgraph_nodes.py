"""
LangGraph Nodes - Wrapping Existing Components

These nodes wrap existing components (HybridRetriever, PodcastAgent) to work
within the LangGraph workflow. This ensures we don't break existing functionality.
"""
import re
from typing import Dict, Any
from core_engine.reasoning.langgraph_state import RetrievalState, QueryPlan
from core_engine.reasoning.intelligent_query_planner import IntelligentQueryPlanner
from core_engine.logging import get_logger


logger = get_logger(__name__)


def plan_query_node(state: RetrievalState) -> RetrievalState:
    """
    Node 1: Intelligent Query Planning.
    
    Uses IntelligentQueryPlanner to:
    - Analyze context (follow-up vs new question)
    - Check domain relevance (reject irrelevant queries)
    - Assess complexity (simple/moderate/complex)
    - Plan retrieval strategy
    """
    query = state["query"]
    conversation_history = state.get("conversation_history", [])
    session_metadata = state.get("session_metadata", {})
    openai_client = state.get("openai_client")
    
    logger.info(
        "langgraph_plan_query",
        extra={"context": {"query": query[:50], "has_history": len(conversation_history) > 0}}
    )
    
    try:
        # Initialize planner if not already done
        if not openai_client:
            logger.warning("langgraph_no_openai_client", extra={"context": {"query": query[:50]}})
            # Fallback to simple plan
            plan = QueryPlan(
                is_follow_up=len(conversation_history) > 0,
                is_relevant=True,
                complexity="moderate",
                intent="knowledge_query",
                needs_decomposition=False,
                sub_queries=[query],
                entities=[],
                retrieval_strategy={
                    "use_rag": True,
                    "use_kg": True,
                    "kg_query_type": "entity_centric",
                    "rag_expansion": False,
                    "iterative": False,
                }
            )
        else:
            # Use Intelligent Query Planner
            planner = IntelligentQueryPlanner(openai_client=openai_client)
            plan = planner.plan(
                query=query,
                conversation_history=conversation_history,
                session_metadata=session_metadata
            )
        
        state["query_plan"] = plan
        
        # If query is out of scope, set should_continue to False
        if not plan.is_relevant:
            state["should_continue"] = False
            # Set answer for out-of-scope queries - use standard rejection message
            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
            state["sources"] = []
            state["metadata"] = {"method": "query_planner", "intent": "out_of_scope", "rag_count": 0, "kg_count": 0}
        else:
            state["should_continue"] = True
        
        logger.info(
            "langgraph_plan_complete",
            extra={
                "context": {
                    "query": query[:50],
                    "is_relevant": plan.is_relevant,
                    "complexity": plan.complexity,
                    "intent": plan.intent,
                    "is_follow_up": plan.is_follow_up,
                }
            }
        )
        
    except Exception as e:
        logger.error(
            "langgraph_plan_error",
            exc_info=True,
            extra={"context": {"query": query[:50], "error": str(e)}}
        )
        # Fallback to simple plan on error
        plan = QueryPlan(
            is_follow_up=len(conversation_history) > 0,
            is_relevant=True,
            complexity="moderate",
            intent="knowledge_query",
            needs_decomposition=False,
            sub_queries=[query],
            entities=[],
            retrieval_strategy={
                "use_rag": True,
                "use_kg": True,
                "kg_query_type": "entity_centric",
                "rag_expansion": False,
                "iterative": False,
            }
        )
        state["query_plan"] = plan
        state["should_continue"] = True
    
    return state


def retrieve_rag_node(state: RetrievalState) -> RetrievalState:
    """
    Node 2: RAG Retrieval using existing HybridRetriever.
    
    Uses query plan to determine:
    - Which queries to retrieve (sub-queries if decomposed)
    - Whether to use RAG at all
    - Whether to expand queries
    
    CRITICAL: For knowledge queries, RAG MUST be called (100% enforcement).
    """
    retriever = state.get("hybrid_retriever")
    plan: QueryPlan = state.get("query_plan")
    query = state["query"]
    
    if not retriever:
        logger.warning("langgraph_no_retriever", extra={"context": {"query": query[:50]}})
        state["rag_results"] = []
        return state
    
    if not plan:
        logger.warning("langgraph_no_plan", extra={"context": {"query": query[:50]}})
        state["rag_results"] = []
        return state
    
    # Get intent to check if this is a knowledge query
    intent = (plan.intent.lower() if plan and hasattr(plan, 'intent') else "") or ""
    allowed_without_results = ["greeting", "conversational", "system_info", "non_query", "clarification"]
    
    # Check if RAG should be used
    retrieval_strategy = plan.retrieval_strategy or {}
    
    # CRITICAL: For knowledge queries, ALWAYS call RAG (100% enforcement)
    if intent not in allowed_without_results:
        # Force RAG to be used for knowledge queries
        if not retrieval_strategy.get("use_rag", True):
            logger.warning(
                "langgraph_rag_forced_for_knowledge_query",
                extra={"context": {"query": query[:50], "intent": intent, "action": "forcing_rag_call"}}
            )
            retrieval_strategy["use_rag"] = True  # Override plan if needed
    
    if not retrieval_strategy.get("use_rag", True):
        logger.info("langgraph_rag_skipped", extra={"context": {"query": query[:50], "reason": "plan says no RAG"}})
        state["rag_results"] = []
        return state
    
    try:
        # Use sub-queries if query was decomposed, otherwise use original
        queries_to_retrieve = plan.sub_queries if plan.needs_decomposition and plan.sub_queries else [query]
        
        rag_results = []
        for q in queries_to_retrieve:
            results = retriever.retrieve(q, use_vector=True, use_graph=False)
            rag_results.extend(results)
        
        # Query expansion if needed (use QueryExpander for intelligent expansion)
        if retrieval_strategy.get("rag_expansion", False):
            try:
                from core_engine.reasoning.query_expander import QueryExpander
                
                # Initialize expander
                expander = QueryExpander(
                    openai_client=state.get("openai_client"),
                    max_variations=3,  # Generate 3 variations per query
                    use_llm=True,
                )
                
                # Expand each query and retrieve
                for q in queries_to_retrieve[:2]:  # Limit to first 2 queries
                    try:
                        # Get context from query plan
                        expansion_context = {
                            "query_type": plan.intent if plan else "knowledge_query",
                            "complexity": plan.complexity if plan else "moderate",
                        }
                        
                        # Expand and retrieve (skip original query since we already retrieved it)
                        expanded_results = expander.expand_and_retrieve(
                            query=q,
                            retriever=retriever,
                            context=expansion_context,
                            skip_original=True,  # Skip original to avoid duplicate retrieval
                        )
                        rag_results.extend(expanded_results)
                        
                        logger.info(
                            "rag_expansion_applied",
                            extra={
                                "context": {
                                    "query": q[:50],
                                    "expanded_results_count": len(expanded_results),
                                }
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            "rag_expansion_failed",
                            extra={"context": {"query": q[:50], "error": str(e)}}
                        )
                        # Fallback: retrieve with original query
                        try:
                            results = retriever.retrieve(q, use_vector=True, use_graph=False)
                            rag_results.extend(results)
                        except Exception as e2:
                            logger.warning("rag_fallback_failed", extra={"context": {"query": q[:50], "error": str(e2)}})
            except ImportError:
                # Fallback to simple expansion if QueryExpander not available
                logger.warning("query_expander_not_available", extra={"context": {"query": query[:50], "fallback": "simple_expansion"}})
                expanded_queries = [
                    f"Tell me more about {q}" for q in queries_to_retrieve[:2]
                ]
                for eq in expanded_queries:
                    try:
                        results = retriever.retrieve(eq, use_vector=True, use_graph=False)
                        rag_results.extend(results)
                    except Exception as e:
                        logger.warning("rag_expansion_failed", extra={"context": {"query": eq, "error": str(e)}})
            except Exception as e:
                logger.error("query_expansion_error", exc_info=True, extra={"context": {"query": query[:50], "error": str(e)}})
                # Fallback: continue with original queries only
        
        state["rag_results"] = rag_results
        
        logger.info(
            "langgraph_rag_retrieved",
            extra={
                "context": {
                    "query": query[:50],
                    "results_count": len(rag_results),
                    "queries_used": len(queries_to_retrieve),
                    "expanded": retrieval_strategy.get("rag_expansion", False)
                }
            }
        )
    except Exception as e:
        logger.error(
            "langgraph_rag_error",
            exc_info=True,
            extra={"context": {"query": query[:50], "error": str(e)}}
        )
        state["rag_results"] = []
        if not state.get("error"):
            state["error"] = f"RAG retrieval failed: {str(e)}"
    
    return state


def retrieve_kg_node(state: RetrievalState) -> RetrievalState:
    """
    Node 3: KG Retrieval using existing agent logic.
    
    Uses query plan to determine:
    - Which queries to search (sub-queries if decomposed)
    - KG query type (entity_centric, multi_hop, cross_episode)
    - Whether to use KG at all
    
    CRITICAL: For knowledge queries, KG MUST be called (100% enforcement).
    """
    agent = state.get("podcast_agent")
    plan: QueryPlan = state.get("query_plan")
    query = state["query"]
    
    if not agent:
        logger.warning("langgraph_no_agent", extra={"context": {"query": query[:50]}})
        state["kg_results"] = []
        return state
    
    if not plan:
        logger.warning("langgraph_no_plan", extra={"context": {"query": query[:50]}})
        state["kg_results"] = []
        return state
    
    # Get intent to check if this is a knowledge query
    intent = (plan.intent.lower() if plan and hasattr(plan, 'intent') else "") or ""
    allowed_without_results = ["greeting", "conversational", "system_info", "non_query", "clarification"]
    
    # Check if KG should be used
    retrieval_strategy = plan.retrieval_strategy or {}
    
    # Skip KG if direct_answer (greetings, etc.) - but ONLY for true greetings
    if retrieval_strategy.get("direct_answer", False) and intent == "greeting":
        logger.info("langgraph_kg_skipped", extra={"context": {"query": query[:50], "reason": "direct_answer_greeting"}})
        state["kg_results"] = []
        return state
    
    # CRITICAL: For knowledge queries, ALWAYS call KG (100% enforcement)
    if intent not in allowed_without_results:
        # Force KG to be used for knowledge queries
        if not retrieval_strategy.get("use_kg", True):
            logger.warning(
                "langgraph_kg_forced_for_knowledge_query",
                extra={"context": {"query": query[:50], "intent": intent, "action": "forcing_kg_call"}}
            )
            retrieval_strategy["use_kg"] = True  # Override plan if needed
    
    if not retrieval_strategy.get("use_kg", True):
        logger.info("langgraph_kg_skipped", extra={"context": {"query": query[:50], "reason": "plan says no KG"}})
        state["kg_results"] = []
        return state
    
    # Use sub-queries if query was decomposed, otherwise use original
    queries_to_search = plan.sub_queries if plan.needs_decomposition and plan.sub_queries else [query]
    
    kg_results = []
    kg_query_type = retrieval_strategy.get("kg_query_type", "entity_centric")
    
    try:
        # Use KG Query Optimizer if available
        try:
            from core_engine.reasoning.kg_query_optimizer import KGQueryOptimizer
            
            # Initialize optimizer
            optimizer = KGQueryOptimizer(
                neo4j_client=state.get("neo4j_client"),
                openai_client=state.get("openai_client"),
                workspace_id=agent.workspace_id if hasattr(agent, 'workspace_id') else "default",
            )
            
            # Determine query type from plan
            query_type_map = {
                "entity_centric": "entity_linking",
                "multi_hop": "multi_hop",
                "cross_episode": "cross_episode",
            }
            optimized_query_type = query_type_map.get(kg_query_type, None)
            
            # Search with optimizer
            for q in queries_to_search:
                try:
                    results = optimizer.search(
                        query=q,
                        query_type=optimized_query_type,
                        max_hops=3,
                        limit=10,
                    )
                    kg_results.extend(results)
                    logger.info(
                        "kg_optimizer_search",
                        extra={
                            "context": {
                                "query": q[:50],
                                "query_type": optimized_query_type,
                                "results_count": len(results),
                            }
                        }
                    )
                except Exception as e:
                    logger.warning("kg_optimizer_search_failed", extra={"context": {"query": q, "error": str(e)}})
                    # Fallback to basic search
                    if hasattr(agent, '_search_knowledge_graph'):
                        try:
                            results = agent._search_knowledge_graph(q)
                            kg_results.extend(results)
                        except Exception as e2:
                            logger.warning("kg_search_fallback_failed", extra={"context": {"query": q, "error": str(e2)}})
        except ImportError:
            # Fallback to basic search if optimizer not available
            logger.warning("kg_optimizer_not_available", extra={"context": {"query": query[:50], "fallback": "basic_search"}})
            if hasattr(agent, '_search_knowledge_graph'):
                for q in queries_to_search:
                    try:
                        results = agent._search_knowledge_graph(q)
                        kg_results.extend(results)
                    except Exception as e_fallback:
                        logger.warning("kg_search_failed", extra={"context": {"query": q, "error": str(e_fallback)}})
        except Exception as e_optimizer:
            # Fallback to basic search on error
            logger.error("kg_optimizer_error", exc_info=True, extra={"context": {"query": query[:50], "error": str(e_optimizer)}})
            if hasattr(agent, '_search_knowledge_graph'):
                for q in queries_to_search:
                    try:
                        results = agent._search_knowledge_graph(q)
                        kg_results.extend(results)
                    except Exception as e_fallback2:
                        logger.warning("kg_search_fallback_failed", extra={"context": {"query": q, "error": str(e_fallback2)}})
        
        state["kg_results"] = kg_results
        
        # CRITICAL CHECK: If RAG=0 AND KG=0, check if query is general knowledge
        # If so, mark as not relevant and block synthesis
        rag_count = len(state.get("rag_results", []))
        kg_count = len(kg_results)
        
        if rag_count == 0 and kg_count == 0:
            # Get intent from query plan (QueryPlan is a dataclass, use .intent attribute)
            query_plan: QueryPlan = state.get("query_plan")
            intent = (query_plan.intent.lower() if query_plan and hasattr(query_plan, 'intent') else "") or ""
            
            # Allow greetings and conversational without results (they don't need RAG/KG)
            allowed_without_results = ["greeting", "conversational", "system_info", "non_query", "clarification"]
            
            # If it's NOT an allowed intent, reject immediately (universal rule)
            if intent not in allowed_without_results:
                logger.warning(
                    "langgraph_no_results_reject",
                    extra={
                        "context": {
                            "query": query[:50],
                            "rag_count": rag_count,
                            "kg_count": kg_count,
                            "intent": intent,
                            "action": "blocking_synthesis_no_results"
                        }
                    }
                )
                state["should_continue"] = False
                state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                state["sources"] = []
                state["metadata"] = {"type": "no_results", "rag_count": 0, "kg_count": 0, "intent": intent}
                return state
            
            # For allowed intents, still check if it's general knowledge (extra safety)
            query_lower = query.lower().strip()
            general_knowledge_patterns = [
                r"what are (the|some|main|key).*issues.*(of|in).*society",
                r"what are (the|some|main|key).*problems.*(of|in).*society",
                r"what is (the|a).*solution.*(to|for).*",
                r"explain.*(society|history|science|philosophy|creativity).*",
            ]
            
            import re
            is_general_knowledge = any(
                re.search(pattern, query_lower, re.IGNORECASE) 
                for pattern in general_knowledge_patterns
            )
            
            # Also check if query doesn't mention podcasts, transcripts, knowledge graph, or specific entities
            podcast_keywords = ["podcast", "transcript", "knowledge graph", "speaker", "episode", "said", "mentioned"]
            has_podcast_reference = any(keyword in query_lower for keyword in podcast_keywords)
            
            if is_general_knowledge and not has_podcast_reference:
                logger.warning(
                    "langgraph_general_knowledge_no_results",
                    extra={
                        "context": {
                            "query": query[:50],
                            "rag_count": rag_count,
                            "kg_count": kg_count,
                            "is_general_knowledge": True,
                            "has_podcast_reference": False,
                            "action": "blocking_synthesis"
                        }
                    }
                )
                # Mark as not relevant to block synthesis
                state["should_continue"] = False
                state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                state["sources"] = []
                state["metadata"] = {"type": "no_results_general_knowledge", "rag_count": 0, "kg_count": 0}
                return state
        
        logger.info(
            "langgraph_kg_retrieved",
            extra={
                "context": {
                    "query": query[:50],
                    "results_count": len(kg_results),
                    "kg_query_type": kg_query_type,
                    "queries_used": len(queries_to_search)
                }
            }
        )
    except Exception as e:
        logger.error(
            "langgraph_kg_error",
            exc_info=True,
            extra={"context": {"query": query[:50], "error": str(e)}}
        )
        state["kg_results"] = []
        if not state.get("error"):
            state["error"] = f"KG retrieval failed: {str(e)}"
    
    return state


def rerank_node(state: RetrievalState) -> RetrievalState:
    """
    Node 4: Reranking using configurable strategy (RRF, MMR, or Hybrid RRF+MMR).
    
    Reads strategy from RERANKING_STRATEGY env var:
    - "rrf": Reciprocal Rank Fusion only
    - "mmr": Maximal Marginal Relevance only
    - "rrf_mmr": Hybrid (RRF then MMR) - recommended
    """
    import os
    from core_engine.reasoning.reranker import Reranker
    
    rag_results = state.get("rag_results", [])
    kg_results = state.get("kg_results", [])
    query = state.get("query", "")
    openai_client = state.get("openai_client")
    
    # Get strategy from environment (default: rrf_mmr)
    strategy = os.getenv("RERANKING_STRATEGY", "rrf_mmr").lower()
    if strategy not in ["rrf", "mmr", "rrf_mmr"]:
        logger.warning(f"Invalid RERANKING_STRATEGY '{strategy}', defaulting to 'rrf_mmr'")
        strategy = "rrf_mmr"
    
    # Initialize reranker with strategy
    reranker = Reranker(
        strategy=strategy,
        k=60,  # Standard RRF constant
        lambda_param=0.5,  # MMR lambda (0.5 = balance relevance/diversity)
        openai_client=openai_client,  # Required for MMR
        embed_model=os.getenv("EMBED_MODEL", "text-embedding-3-large"),
    )
    
    # Rerank results
    reranked = reranker.rerank(
        rag_results=rag_results,
        kg_results=kg_results,
        query=query,
    )
    
    state["reranked_results"] = reranked
    
    logger.info(
        "langgraph_reranked",
        extra={
            "context": {
                "strategy": strategy,
                "rag_count": len(rag_results),
                "kg_count": len(kg_results),
                "reranked_count": len(reranked),
                "query": query[:50] if query else None,
            }
        }
    )
    
    return state


def synthesize_node(state: RetrievalState) -> RetrievalState:
    """
    Node 5: Synthesis using existing PodcastAgent.
    
    Handles:
    - Direct answers (greetings) - uses agent.run() without retrieval
    - Regular queries - uses agent.run() (which will use pre-retrieved results if available)
    - Out-of-scope queries - already handled in plan_query_node
    """
    query = state.get("query", "")
    plan: QueryPlan = state.get("query_plan")
    agent = state.get("podcast_agent")
    rag_results = state.get("rag_results", [])
    kg_results = state.get("kg_results", [])
    conversation_history = state.get("conversation_history", [])
    reranked_results = state.get("reranked_results", [])
    
    # UNIVERSAL CHECK: If RAG=0 AND KG=0, ALWAYS reject (no exceptions for knowledge queries)
    rag_count = len(rag_results)
    kg_count = len(kg_results)
    
    # Get intent from query plan to check if it's a greeting/conversational (these don't need results)
    # QueryPlan is a dataclass, so use .intent attribute, not .get()
    intent = (plan.intent.lower() if plan and hasattr(plan, 'intent') else "") or ""
    
    # Allow ONLY these intents without results (they don't need RAG/KG)
    # STRICT: Only greetings and true conversational queries are allowed
    allowed_without_results = ["greeting", "conversational", "system_info", "non_query", "clarification"]
    
    # CRITICAL CHECK: If RAG=0 AND KG=0, check intent STRICTLY
    if rag_count == 0 and kg_count == 0:
        # Additional check: Is this query asking a question that requires knowledge?
        # Questions starting with "what", "who", "how", "why", "when", "where" typically need results
        question_patterns = [
            r"^(what|who|how|why|when|where|are|is|can|do|does|did|will|would|should|tell me|explain|describe|list|show|give|find|search)",
            r"\?$",  # Ends with question mark
        ]
        query_lower = query.lower().strip()
        is_question = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in question_patterns)
        
        # If it's a question AND intent is not in allowed list, REJECT
        if is_question and intent not in allowed_without_results:
            logger.warning(
                "langgraph_universal_no_results_reject",
                extra={
                    "context": {
                        "query": query[:50],
                        "rag_count": 0,
                        "kg_count": 0,
                        "intent": intent,
                        "is_question": True,
                        "action": "universal_reject_no_results"
                    }
                }
            )
            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
            state["sources"] = []
            state["metadata"] = {"type": "no_results", "rag_count": 0, "kg_count": 0, "intent": intent}
            state["should_continue"] = False
            return state
        
        # If intent is not in allowed list (even if not a question), REJECT
        if intent not in allowed_without_results:
            logger.warning(
                "langgraph_universal_no_results_reject",
                extra={
                    "context": {
                        "query": query[:50],
                        "rag_count": 0,
                        "kg_count": 0,
                        "intent": intent,
                        "is_question": False,
                        "action": "universal_reject_no_results"
                    }
                }
            )
            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
            state["sources"] = []
            state["metadata"] = {"type": "no_results", "rag_count": 0, "kg_count": 0, "intent": intent}
            state["should_continue"] = False
            return state
    
    if not agent:
        state["answer"] = "Error: Agent not available"
        state["sources"] = []
        state["metadata"] = {}
        return state
    
    # Check if answer already set (out-of-scope queries)
    if state.get("answer") and not state.get("should_continue", True):
        logger.info("langgraph_synthesis_skipped", extra={"context": {"query": query[:50], "reason": "out_of_scope"}})
        return state
    
    try:
        session_metadata = state.get("session_metadata", {})
        
        # Check if this is a direct answer query (greeting)
        retrieval_strategy = plan.retrieval_strategy if plan else {}
        intent = (plan.intent.lower() if plan and hasattr(plan, 'intent') else "") or ""
        
        # CRITICAL: Only allow direct_answer for TRUE greetings/conversational
        # If RAG=0, KG=0 and it's NOT a greeting, reject immediately
        # This is a SECOND CHECK to catch any queries that slipped through
        if rag_count == 0 and kg_count == 0:
            allowed_intents = ["greeting", "conversational", "system_info", "non_query", "clarification"]
            
            # Additional check: Is this a question that requires knowledge?
            question_patterns = [
                r"^(what|who|how|why|when|where|are|is|can|do|does|did|will|would|should|tell me|explain|describe|list|show|give|find|search)",
                r"\?$",  # Ends with question mark
            ]
            query_lower = query.lower().strip()
            is_question = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in question_patterns)
            
            # STRICT: If it's a question OR intent is not allowed, REJECT
            if is_question or intent not in allowed_intents:
                # This is a knowledge query with no results - REJECT
                logger.warning(
                    "langgraph_synthesis_blocked_no_results",
                    extra={
                        "context": {
                            "query": query[:50],
                            "rag_count": 0,
                            "kg_count": 0,
                            "intent": intent,
                            "is_question": is_question,
                            "direct_answer": retrieval_strategy.get("direct_answer", False),
                            "action": "rejecting_knowledge_query_no_results"
                        }
                    }
                )
                state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                state["sources"] = []
                state["metadata"] = {"type": "no_results", "rag_count": 0, "kg_count": 0, "intent": intent}
                state["should_continue"] = False
                return state
        
        # Only use direct_answer for TRUE greetings (intent must be greeting)
        # CRITICAL: Even for greetings, if RAG=0 and KG=0 and it's NOT a true greeting, reject
        if retrieval_strategy.get("direct_answer", False) and intent == "greeting":
            # TRIPLE CHECK: Verify it's a TRUE greeting (not misclassified)
            query_lower = query.lower().strip()
            true_greeting_patterns = ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye"]
            is_true_greeting = query_lower in true_greeting_patterns or query_lower in [p + "!" for p in true_greeting_patterns] or query_lower in [p + "." for p in true_greeting_patterns]
            
            # DOUBLE CHECK: Only allow if it's truly a greeting AND we have no results
            # If we somehow have results, use them instead
            if rag_count == 0 and kg_count == 0 and is_true_greeting:
                # For TRUE greetings ONLY, use agent.run() which will handle it appropriately
                logger.info("langgraph_direct_answer_true_greeting", extra={"context": {"query": query[:50], "intent": intent, "is_true_greeting": is_true_greeting}})
                response = agent.run(
                    query=query,
                    conversation_history=conversation_history,
                    session_metadata=session_metadata,
                )
                state["answer"] = response.answer if hasattr(response, 'answer') else ""
                state["sources"] = response.sources if hasattr(response, 'sources') else []
                state["metadata"] = response.metadata if hasattr(response, 'metadata') else {}
            elif rag_count == 0 and kg_count == 0 and not is_true_greeting:
                # Misclassified as greeting but it's actually a question - REJECT
                logger.error(
                    "langgraph_direct_answer_rejected_not_true_greeting",
                    extra={
                        "context": {
                            "query": query[:50],
                            "intent": intent,
                            "is_true_greeting": is_true_greeting,
                            "rag_count": 0,
                            "kg_count": 0,
                            "action": "rejecting_misclassified_greeting"
                        }
                    }
                )
                state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                state["sources"] = []
                state["metadata"] = {"type": "no_results", "rag_count": 0, "kg_count": 0, "intent": intent}
                state["should_continue"] = False
                return state
            else:
                # We have results, so use them instead of direct answer
                logger.info("langgraph_direct_answer_skipped_has_results", extra={"context": {"query": query[:50], "rag_count": rag_count, "kg_count": kg_count}})
                # Fall through to use pre-retrieved results
                pass
        else:
            # Use pre-retrieved results from RAG/KG nodes
            # CRITICAL: Check if we have results - if not, return "no information found"
            # Also check original RAG/KG counts to ensure retrieval actually happened
            has_rag_results = len(rag_results) > 0
            has_kg_results = len(kg_results) > 0
            has_reranked_results = len(reranked_results) > 0
            
            # If no retrieval results AND no reranked results, return "no information found"
            if not has_rag_results and not has_kg_results and not has_reranked_results:
                logger.warning("langgraph_no_results", extra={"context": {"query": query[:50], "rag_count": 0, "kg_count": 0}})
                state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                state["sources"] = []
                state["metadata"] = {"type": "no_results", "rag_count": 0, "kg_count": 0}
            elif not has_reranked_results:
                # Reranked results empty but original results exist (shouldn't happen, but handle it)
                logger.warning("langgraph_reranked_results_empty", extra={"context": {"query": query[:50], "rag_count": len(rag_results), "kg_count": len(kg_results)}})
                state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                state["sources"] = []
                state["metadata"] = {"type": "no_results", "rag_count": len(rag_results), "kg_count": len(kg_results)}
            else:
                # Use reranked results (from RRF) for synthesis
                # Split reranked results back into RAG and KG for synthesis
                # (agent._synthesize_answer expects separate RAG/KG lists)
                reranked_rag = [r for r in reranked_results if r.get("source_type") == "rag"]
                reranked_kg = [r for r in reranked_results if r.get("source_type") == "kg"]
                
                # CRITICAL: Double-check that we have actual content in reranked results
                # Filter out empty/invalid results
                valid_rag = [r for r in reranked_rag if r.get("text") or r.get("concept")]
                valid_kg = [r for r in reranked_kg if r.get("text") or r.get("concept") or r.get("description")]
                
                # If no valid results after filtering, return "no information found"
                if not valid_rag and not valid_kg:
                    logger.warning("langgraph_no_valid_results_after_filtering", extra={"context": {"query": query[:50], "reranked_count": len(reranked_results)}})
                    state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                    state["sources"] = []
                    state["metadata"] = {"type": "no_results", "rag_count": len(rag_results), "kg_count": len(kg_results)}
                else:
                    # Use top reranked results (already sorted by RRF score)
                    top_rag = valid_rag[:5]
                    top_kg = valid_kg[:10]
                    
                    # Resolve query (for pronoun resolution)
                    resolved_query = agent._resolve_pronouns(query, session_metadata) if hasattr(agent, '_resolve_pronouns') else query
                    
                    # FINAL CHECK: Ensure we have valid results before synthesis
                    # This is a hard stop - if no valid results, don't synthesize
                    top_rag_count = len(top_rag) if top_rag else 0
                    top_kg_count = len(top_kg) if top_kg else 0
                    
                    # CRITICAL: Check original counts too - if both are 0, NEVER synthesize
                    original_rag_count = len(rag_results)
                    original_kg_count = len(kg_results)
                    
                    # Explicit check: if both original counts are 0, don't synthesize (regardless of reranked)
                    if original_rag_count == 0 and original_kg_count == 0:
                        # Check if this is a question
                        question_patterns = [
                            r"^(what|who|how|why|when|where|are|is|can|do|does|did|will|would|should|tell me|explain|describe|list|show|give|find|search)",
                            r"\?$",
                        ]
                        query_lower = query.lower().strip()
                        is_question = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in question_patterns)
                        
                        # Check if it's a true greeting (very strict)
                        is_true_greeting = (
                            intent == "greeting" and 
                            not is_question and
                            query_lower in ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye", "hmm", "ok", "okay"]
                        )
                        
                        # REJECT if it's a question OR intent requires results OR not a true greeting
                        if is_question or (intent not in allowed_without_results) or (not is_true_greeting):
                            logger.error(
                                "langgraph_synthesis_blocked_no_results_original",
                                extra={
                                    "context": {
                                        "query": query[:50],
                                        "original_rag_count": original_rag_count,
                                        "original_kg_count": original_kg_count,
                                        "top_rag_count": top_rag_count,
                                        "top_kg_count": top_kg_count,
                                        "intent": intent,
                                        "is_question": is_question,
                                        "is_true_greeting": is_true_greeting,
                                        "message": "HARD STOP: original_rag_count=0 AND original_kg_count=0, blocking synthesis"
                                    }
                                }
                            )
                            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                            state["sources"] = []
                            state["metadata"] = {"type": "no_results", "rag_count": 0, "kg_count": 0, "intent": intent}
                            state["should_continue"] = False
                            return state
                    
                    # Explicit check: if both top counts are 0, don't synthesize
                    if top_rag_count == 0 and top_kg_count == 0:
                        logger.error(
                            "langgraph_synthesis_blocked_no_valid_results",
                            extra={
                                "context": {
                                    "query": query[:50],
                                    "top_rag_count": top_rag_count,
                                    "top_kg_count": top_kg_count,
                                    "valid_rag_count": len(valid_rag),
                                    "valid_kg_count": len(valid_kg),
                                    "reranked_count": len(reranked_results),
                                    "original_rag_count": len(rag_results),
                                    "original_kg_count": len(kg_results),
                                    "message": "HARD STOP: top_rag_count=0 AND top_kg_count=0, blocking synthesis"
                                }
                            }
                        )
                        state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                        state["sources"] = []
                        state["metadata"] = {"type": "no_results", "rag_count": len(rag_results), "kg_count": len(kg_results)}
                    else:
                        # Log before synthesis
                        logger.info(
                            "langgraph_synthesis_proceeding",
                            extra={
                                "context": {
                                    "query": query[:50],
                                    "top_rag_count": top_rag_count,
                                    "top_kg_count": top_kg_count,
                                    "original_rag_count": original_rag_count,
                                    "original_kg_count": original_kg_count,
                                    "will_call_llm": True
                                }
                            }
                        )
                        
                        # Resolve query (for pronoun resolution)
                        resolved_query = agent._resolve_pronouns(query, session_metadata) if hasattr(agent, '_resolve_pronouns') else query
                        
                        # Synthesize answer using reranked results
                        answer = agent._synthesize_answer(
                            query=query,
                            resolved_query=resolved_query,
                            rag_results=top_rag,
                            kg_results=top_kg,
                            conversation_history=conversation_history,
                            session_metadata=session_metadata,
                        )
                        
                        # Extract sources from reranked results
                        sources = agent._extract_sources(top_rag, top_kg) if hasattr(agent, '_extract_sources') else []
                        
                        state["answer"] = answer
                        state["sources"] = sources
                        
                        # Build metadata
                        rag_count = len(rag_results)  # Original counts
                        kg_count = len(kg_results)
                        state["metadata"] = {
                            "method": "langgraph_rrf",
                            "rag_count": rag_count,
                            "kg_count": kg_count,
                            "reranked_count": len(reranked_results),
                            "sources": sources,
                        }
        
        logger.info(
            "langgraph_synthesized",
            extra={"context": {
                "query": query[:50],
                "answer_length": len(state.get("answer", "")),
                "sources_count": len(state.get("sources", [])),
                "intent": plan.intent if plan else "unknown",
            }}
        )
    except Exception as e:
        logger.error(
            "langgraph_synthesis_error",
            exc_info=True,
            extra={"context": {"query": query[:50], "error": str(e)}}
        )
        state["answer"] = f"Error synthesizing answer: {str(e)}"
        state["sources"] = []
        state["metadata"] = {"error": str(e)}
        state["error"] = str(e)
    
    return state


def self_reflect_node(state: RetrievalState) -> RetrievalState:
    """
    Node 6: Self-Reflection and Self-Grading - FINAL QUALITY CHECK.
    
    This is the LAST LAYER that ensures:
    1. Answer was generated ONLY if results exist (RAG>0 OR KG>0)
    2. Answer quality is appropriate for the query
    3. No hallucination - answer must be grounded in results
    
    CRITICAL: This is the final gate before returning to user.
    """
    query = state.get("query", "")
    answer = state.get("answer", "")
    rag_results = state.get("rag_results", [])
    kg_results = state.get("kg_results", [])
    sources = state.get("sources", [])
    plan: QueryPlan = state.get("query_plan")
    openai_client = state.get("openai_client")
    
    rag_count = len(rag_results)
    kg_count = len(kg_results)
    intent = (plan.intent.lower() if plan and hasattr(plan, 'intent') else "") or ""
    
    # ALLOWED intents that don't need results
    allowed_without_results = ["greeting", "conversational", "system_info", "non_query", "clarification"]
    
    # CRITICAL: Log entry to self-reflection node - this MUST run
    logger.info(
        "langgraph_self_reflection_start",
        extra={
            "context": {
                "query": query[:50],
                "rag_count": rag_count,
                "kg_count": kg_count,
                "intent": intent,
                "answer_length": len(answer),
                "sources_count": len(sources),
                "has_answer": bool(answer),
                "answer_preview": answer[:100] if answer else None,
            }
        }
    )
    
    # CRITICAL: If answer exists but RAG=0 and KG=0, this is SUSPICIOUS - log it
    if answer and rag_count == 0 and kg_count == 0:
        logger.error(
            "langgraph_self_reflection_suspicious_answer",
            extra={
                "context": {
                    "query": query[:50],
                    "rag_count": 0,
                    "kg_count": 0,
                    "answer_length": len(answer),
                    "answer_preview": answer[:200],
                    "intent": intent,
                    "action": "DETECTED_SUSPICIOUS_ANSWER_WITH_NO_RESULTS"
                }
            }
        )
    
    # ============================================================
    # CHECK 1: HARD STOP - If RAG=0 AND KG=0, REJECT IMMEDIATELY
    # ============================================================
    # CRITICAL: This is the FINAL GATE - be extremely aggressive
    # REJECT ANY answer if RAG=0 AND KG=0, UNLESS it's a TRUE greeting
    # THIS CHECK RUNS FIRST - BEFORE ANY OTHER LOGIC
    if rag_count == 0 and kg_count == 0:
        # Check if this is a question that requires knowledge
        question_patterns = [
            r"^(what|who|how|why|when|where|are|is|can|do|does|did|will|would|should|tell me|explain|describe|list|show|give|find|search)",
            r"\?$",  # Ends with question mark
        ]
        query_lower = query.lower().strip()
        is_question = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in question_patterns)
        
        # Check for knowledge-seeking phrases
        knowledge_phrases = [
            "issues", "problems", "solutions", "concepts", "ideas", "practices",
            "what did", "what are", "what is", "who is", "how does", "why does",
            "main", "society", "translate", "weather", "current", "pm of", "prime minister"
        ]
        has_knowledge_phrase = any(phrase in query_lower for phrase in knowledge_phrases)
        
        # CRITICAL: Only allow TRUE greetings - everything else with no results gets rejected
        # Even "conversational" queries with no results should be rejected if they're questions
        true_greeting_patterns = ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye", "hmm", "ok", "okay"]
        is_true_greeting = (
            intent == "greeting" and 
            not is_question and
            not has_knowledge_phrase and
            (query_lower in true_greeting_patterns or 
             query_lower in [p + "!" for p in true_greeting_patterns] or 
             query_lower in [p + "." for p in true_greeting_patterns])
        )
        
        # REJECT if:
        # 1. It's a question (regardless of intent)
        # 2. It has knowledge-seeking phrases (regardless of intent)
        # 3. Intent requires results (not in allowed list)
        # 4. Answer was generated but it's NOT a true greeting
        # CRITICAL: If answer exists and RAG=0, KG=0, ALWAYS reject unless it's a true greeting
        # THIS IS THE MOST AGGRESSIVE CHECK - reject everything unless it's a true greeting
        should_reject = (
            is_question or 
            has_knowledge_phrase or 
            (intent not in allowed_without_results) or 
            (answer and not is_true_greeting) or
            (answer and len(answer) > 50)  # If answer is long, it's definitely not a greeting
        )
        
        if should_reject:
            logger.error(
                "langgraph_self_reflection_reject_no_results",
                extra={
                    "context": {
                        "query": query[:50],
                        "rag_count": 0,
                        "kg_count": 0,
                        "intent": intent,
                        "is_question": is_question,
                        "has_knowledge_phrase": has_knowledge_phrase,
                        "is_true_greeting": is_true_greeting,
                        "answer_was_generated": bool(answer),
                        "answer_length": len(answer) if answer else 0,
                        "action": "FINAL_REJECT_NO_RESULTS"
                    }
                }
            )
            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
            state["sources"] = []
            state["metadata"] = {
                **state.get("metadata", {}),
                "type": "no_results",
                "rag_count": 0,
                "kg_count": 0,
                "intent": intent,
                "self_reflection": "rejected_no_results"
            }
            state["should_continue"] = False
            return state
    
    # ============================================================
    # CHECK 2: If answer exists but no sources, REJECT
    # ============================================================
    if answer and len(sources) == 0 and rag_count == 0 and kg_count == 0:
        # Answer was generated but no sources - this is suspicious
        if intent not in allowed_without_results:
            logger.error(
                "langgraph_self_reflection_reject_no_sources",
                extra={
                    "context": {
                        "query": query[:50],
                        "rag_count": 0,
                        "kg_count": 0,
                        "sources_count": 0,
                        "intent": intent,
                        "action": "FINAL_REJECT_NO_SOURCES"
                    }
                }
            )
            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
            state["sources"] = []
            state["metadata"] = {
                **state.get("metadata", {}),
                "type": "no_results",
                "rag_count": 0,
                "kg_count": 0,
                "intent": intent,
                "self_reflection": "rejected_no_sources"
            }
            state["should_continue"] = False
            return state
    
    # ============================================================
    # CHECK 3: LLM-Based Self-Grading (if OpenAI available)
    # ============================================================
    if openai_client and answer and rag_count == 0 and kg_count == 0:
        # Double-check with LLM if answer is appropriate
        try:
            grading_prompt = f"""You are a quality checker for a Podcast Intelligence Assistant.

CRITICAL RULE: The assistant should ONLY answer questions if it has information from podcast transcripts or knowledge graph.

Query: {query}
Answer Generated: {answer}
RAG Results: {rag_count}
KG Results: {kg_count}
Intent: {intent}

Check:
1. Is this a knowledge question that requires information from podcasts?
2. Were any results retrieved (RAG or KG)?
3. Is the answer appropriate given NO results were found?

If this is a knowledge question with NO results, the answer should be REJECTED.

Return JSON:
{{
    "should_reject": bool,
    "reason": "explanation",
    "confidence": 0.0-1.0
}}"""
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": grading_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            import json
            grading_result = json.loads(response.choices[0].message.content)
            
            if grading_result.get("should_reject", False) and grading_result.get("confidence", 0) > 0.7:
                logger.error(
                    "langgraph_self_reflection_llm_reject",
                    extra={
                        "context": {
                            "query": query[:50],
                            "rag_count": 0,
                            "kg_count": 0,
                            "reason": grading_result.get("reason"),
                            "confidence": grading_result.get("confidence"),
                            "action": "FINAL_REJECT_LLM_GRADING"
                        }
                    }
                )
                state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
                state["sources"] = []
                state["metadata"] = {
                    **state.get("metadata", {}),
                    "type": "no_results",
                    "rag_count": 0,
                    "kg_count": 0,
                    "intent": intent,
                    "self_reflection": "rejected_llm_grading",
                    "grading_reason": grading_result.get("reason")
                }
                state["should_continue"] = False
                return state
        except Exception as e:
            logger.warning(
                "langgraph_self_reflection_llm_failed",
                extra={"context": {"error": str(e), "query": query[:50]}}
            )
            # If LLM grading fails, fall back to pattern-based check (already done above)
            pass
    
    # ============================================================
    # CHECK 4: Verify tools were called for knowledge queries
    # ============================================================
    if intent not in allowed_without_results:
        # For knowledge queries, tools MUST have been called
        if rag_count == 0 and kg_count == 0:
            # Tools were NOT called but should have been
            logger.error(
                "langgraph_self_reflection_tools_not_called",
                extra={
                    "context": {
                        "query": query[:50],
                        "intent": intent,
                        "rag_count": 0,
                        "kg_count": 0,
                        "action": "FINAL_REJECT_TOOLS_NOT_CALLED"
                    }
                }
            )
            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
            state["sources"] = []
            state["metadata"] = {
                **state.get("metadata", {}),
                "type": "no_results",
                "rag_count": 0,
                "kg_count": 0,
                "intent": intent,
                "self_reflection": "rejected_tools_not_called"
            }
            state["should_continue"] = False
            return state
    
    # ============================================================
    # FINAL SAFETY CHECK: If answer exists but RAG=0, KG=0, REJECT
    # ============================================================
    # This is the absolute final check - if we somehow got here with an answer but no results, reject
    # CRITICAL: This check is MORE aggressive - it rejects ANY answer with no results unless it's a true greeting
    if answer and rag_count == 0 and kg_count == 0:
        query_lower = query.lower().strip()
        true_greeting_patterns = ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye", "hmm", "ok", "okay"]
        
        # Check if it's a question
        question_patterns = [
            r"^(what|who|how|why|when|where|are|is|can|do|does|did|will|would|should|tell me|explain|describe|list|show|give|find|search)",
            r"\?$",
        ]
        is_question = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in question_patterns)
        
        # Check for knowledge phrases
        knowledge_phrases = [
            "issues", "problems", "solutions", "concepts", "ideas", "practices",
            "society", "societal", "main", "translate", "weather", "current", "pm of", "prime minister"
        ]
        has_knowledge_phrase = any(phrase in query_lower for phrase in knowledge_phrases)
        
        is_true_greeting = (
            intent == "greeting" and 
            not is_question and
            not has_knowledge_phrase and
            (query_lower in true_greeting_patterns or 
             query_lower in [p + "!" for p in true_greeting_patterns] or 
             query_lower in [p + "." for p in true_greeting_patterns])
        )
        
        # REJECT if it's a question, has knowledge phrases, or is NOT a true greeting
        if is_question or has_knowledge_phrase or not is_true_greeting:
            logger.error(
                "langgraph_self_reflection_final_safety_reject",
                extra={
                    "context": {
                        "query": query[:50],
                        "rag_count": 0,
                        "kg_count": 0,
                        "intent": intent,
                        "answer_length": len(answer),
                        "is_question": is_question,
                        "has_knowledge_phrase": has_knowledge_phrase,
                        "is_true_greeting": is_true_greeting,
                        "action": "FINAL_SAFETY_REJECT"
                    }
                }
            )
            state["answer"] = "I couldn't find information about that in the podcast knowledge base. Could you rephrase your question or ask about a specific topic related to philosophy, creativity, coaching, or personal development from the podcasts?"
            state["sources"] = []
            state["metadata"] = {
                **state.get("metadata", {}),
                "type": "no_results",
                "rag_count": 0,
                "kg_count": 0,
                "intent": intent,
                "self_reflection": "rejected_final_safety"
            }
            state["should_continue"] = False
            return state
    
    # ============================================================
    # PASS: Answer is appropriate
    # ============================================================
    logger.info(
        "langgraph_self_reflection_pass",
        extra={
            "context": {
                "query": query[:50],
                "rag_count": rag_count,
                "kg_count": kg_count,
                "intent": intent,
                "sources_count": len(sources),
                "answer_length": len(answer),
                "self_reflection": "passed"
            }
        }
    )
    
    # Add self-reflection metadata
    state["metadata"] = {
        **state.get("metadata", {}),
        "self_reflection": "passed",
        "rag_count": rag_count,
        "kg_count": kg_count,
    }
    
    return state
