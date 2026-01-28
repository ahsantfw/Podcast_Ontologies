"""
Main reasoning interface - AGENT-BASED ARCHITECTURE

The agent autonomously decides how to answer questions.
RAG and KG are tools the agent can use when needed.

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENT (LLM Brain)                              │
│  - Understands user intent                                               │
│  - Decides which tools to use (or none)                                  │
│  - Synthesizes final answer                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  RAG Tool │   │  KG Tool  │   │ Memory    │
            │ (Qdrant)  │   │ (Neo4j)   │   │ (Session) │
            └───────────┘   └───────────┘   └───────────┘
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import timedelta
from contextlib import contextmanager

from core_engine.kg.neo4j_client import Neo4jClient, get_neo4j_client
from core_engine.reasoning.session_manager import SessionManager, QuerySession
from core_engine.reasoning.query_generator_v2 import IntelligentQueryGenerator
from core_engine.reasoning.cypher_chain import KGCypherChain
from core_engine.reasoning.hybrid_retriever import HybridRetriever
from core_engine.reasoning.multi_hop import MultiHopReasoner
from core_engine.reasoning.agent_tools import KGTools
from core_engine.reasoning.query_templates import QueryTemplates
from core_engine.reasoning.agent import PodcastAgent  # The brain of the system
from core_engine.logging import get_logger


class KGReasoner:
    """
    Main reasoning interface for querying the knowledge graph.
    Combines all Phase 7 components with session management.
    """

    def __init__(
        self,
        neo4j_client: Optional[Neo4jClient] = None,
        workspace_id: Optional[str] = None,
        use_llm: bool = True,
        use_hybrid: bool = True,
        model: str = "gpt-4.1",  # Use latest model for best reasoning
        session_timeout_hours: int = 24,
    ):
        """
        Initialize KG reasoner.

        Args:
            neo4j_client: Neo4j client (created if not provided)
            workspace_id: Workspace identifier
            use_llm: Whether to use LLM for query generation
            use_hybrid: Whether to use hybrid retrieval
            model: OpenAI model name
            session_timeout_hours: Session timeout in hours
        """
        self.workspace_id = workspace_id or "default"
        self.use_llm = use_llm
        self.use_hybrid = use_hybrid
        self.model = model  # Store model for answer synthesis
        self.model = model  # Store model for answer synthesis
        
        # Initialize Neo4j client
        if neo4j_client is None:
            self.neo4j_client = get_neo4j_client(workspace_id=self.workspace_id)
            self._owns_client = True
        else:
            self.neo4j_client = neo4j_client
            self._owns_client = False
        
        self.logger = get_logger(
            "core_engine.reasoning.reasoning",
            workspace_id=self.workspace_id,
        )
        
        # Initialize components
        self.session_manager = SessionManager(
            workspace_id=self.workspace_id,
            session_timeout=timedelta(hours=session_timeout_hours),
        )
        
        self.query_generator = IntelligentQueryGenerator(
            self.neo4j_client,
            workspace_id=self.workspace_id,
            model=model,  # Pass model to query generator
        )
        
        # Initialize LLM chain if requested
        self.cypher_chain = None
        if use_llm:
            try:
                self.cypher_chain = KGCypherChain(
                    neo4j_client=self.neo4j_client,
                    model=model,
                    workspace_id=self.workspace_id,
                )
            except Exception as e:
                self.logger.warning(
                    "cypher_chain_init_failed",
                    extra={"context": {"error": str(e)}},
                )
        
        # Initialize hybrid retriever if requested
        self.hybrid_retriever = None
        if use_hybrid:
            try:
                # Use workspace-specific collection name: {workspace_id}_chunks
                collection_name = f"{self.workspace_id}_chunks"
                self.hybrid_retriever = HybridRetriever(
                    neo4j_client=self.neo4j_client,
                    workspace_id=self.workspace_id,
                    qdrant_collection=collection_name,  # Use workspace-specific collection
                )
            except Exception as e:
                self.logger.warning(
                    "hybrid_retriever_init_failed",
                    extra={"context": {"error": str(e)}},
                )
        
        self.multi_hop = MultiHopReasoner(
            self.neo4j_client,
            workspace_id=self.workspace_id,
        )
        
        self.kg_tools = KGTools(
            neo4j_client=self.neo4j_client,
            workspace_id=self.workspace_id,
            hybrid_retriever=self.hybrid_retriever,
        )
        
        self.query_templates = QueryTemplates()
        
        # Initialize the AGENT - the brain of the system
        # Agent autonomously decides when to use RAG/KG tools
        self.agent = PodcastAgent(
            workspace_id=self.workspace_id,
            model=model,
            neo4j_client=self.neo4j_client,
            hybrid_retriever=self.hybrid_retriever,
        )
        
        # Keep use_agent flag for gradual migration
        self.use_agent = True  # Set to True to use agent-based architecture
        
        self.logger.info("kg_reasoner_initialized", extra={"use_agent": self.use_agent})

    def query(
        self,
        question: str,
        session_id: Optional[str] = None,
        use_llm: Optional[bool] = None,
        use_hybrid: Optional[bool] = None,
        style: str = "casual",
        tone: str = "warm",
    ) -> Dict[str, Any]:
        """
        Query using the AGENT-BASED architecture.
        
        The agent autonomously decides:
        - Whether to use tools (RAG/KG) or respond directly
        - Which tools to use
        - How to synthesize the final answer

        Args:
            question: Natural language question
            session_id: Optional session ID for conversation context
            use_llm: Override default LLM usage (ignored in agent mode)
            use_hybrid: Override default hybrid usage (ignored in agent mode)
            style: Response style (casual, professional, academic, concise, detailed)
            tone: Response tone (warm, neutral, formal, enthusiastic)

        Returns:
            Query result with answer and metadata
        """
        # Get or create session
        session = self.session_manager.get_or_create_session(
            session_id=session_id,
            workspace_id=self.workspace_id,
        )
        
        # Store style and tone in session metadata
        session.metadata["style"] = style
        session.metadata["tone"] = tone
        
        # Add user message to session
        session.add_message("user", question)
        
        # Get conversation history for context
        conversation_history = [
            msg.to_dict() for msg in session.get_conversation_history(max_messages=10)
        ]
        
        self.logger.info(
            "agent_query_start",
            extra={"context": {"question": question[:50], "session_id": session.session_id, "style": style, "tone": tone}}
        )
        
        try:
            # =====================================================
            # RUN THE AGENT
            # Agent autonomously decides what to do
            # =====================================================
            agent_response = self.agent.run(
                query=question,
                conversation_history=conversation_history,
                session_metadata=session.metadata,
            )
            
            # Log what the agent did
            self.logger.info(
                "agent_query_complete",
                extra={
                    "context": {
                        "tools_used": agent_response.tools_used,
                        "sources_count": len(agent_response.sources),
                    }
                }
            )
            
            # Prepare metadata with sources, rag_count, and kg_count
            rag_count = len([s for s in agent_response.sources if s.get("type") == "transcript"])
            kg_count = len([s for s in agent_response.sources if s.get("type") == "knowledge_graph"])
            message_metadata = {
                "method": agent_response.metadata.get("method", "agent"),
                "rag_count": rag_count,
                "kg_count": kg_count,
                "sources": agent_response.sources,  # Include sources in metadata for persistence
            }
            
            # Add assistant response to session with metadata
            if agent_response.answer:
                session.add_message("assistant", agent_response.answer, metadata=message_metadata)
            
            # Log session metadata after agent processing
            self.logger.info(
                "session_metadata_after_agent",
                extra={
                    "context": {
                        "user_name": session.metadata.get("user_name"),
                        "active_entity": session.metadata.get("active_entity"),
                        "user_facts": session.metadata.get("user_facts"),
                    }
                }
            )
            
            # Save session (metadata is updated in-place by agent)
            self._save_session_to_db(session)
            
            # Build result
            result = {
                "answer": agent_response.answer,
                "session_id": session.session_id,
                "sources": agent_response.sources,
                "intermediate_steps": [],
                "metadata": {
                    "method": "agent",
                    "tools_used": agent_response.tools_used,
                    "rag_count": len([s for s in agent_response.sources if s.get("type") == "transcript"]),
                    "kg_count": len([s for s in agent_response.sources if s.get("type") == "knowledge_graph"]),
                    **agent_response.metadata,
                },
            }
            
            return result
            
        except Exception as e:
            self.logger.error(
                "query_failed",
                exc_info=True,
                extra={"context": {"question": question[:100], "error": str(e)}},
            )
            error_msg = f"Query failed: {str(e)}"
            session.add_message("assistant", error_msg, metadata={"error": str(e)})
            # Save session even if there's an error
            self._save_session_to_db(session)
            raise
    
    def query_streaming(
        self,
        question: str,
        session_id: Optional[str] = None,
        style: str = "casual",
        tone: str = "warm",
    ):
        """
        Query with streaming response - yields answer chunks as they're generated.
        
        Args:
            question: Natural language question
            session_id: Optional session ID for conversation context
            style: Response style
            tone: Response tone
            
        Yields:
            Dict with 'chunk' (text) and 'done' (bool) keys
        """
        # Get or create session
        session = self.session_manager.get_or_create_session(
            session_id=session_id,
            workspace_id=self.workspace_id,
        )
        
        # Store style and tone in session metadata
        session.metadata["style"] = style
        session.metadata["tone"] = tone
        
        # Add user message to session
        session.add_message("user", question)
        
        # Get conversation history for context
        conversation_history = [
            msg.to_dict() for msg in session.get_conversation_history(max_messages=10)
        ]
        
        self.logger.info(
            "agent_query_streaming_start",
            extra={"context": {"question": question[:50], "session_id": session.session_id}}
        )
        
        try:
            # Classify intent first (non-streaming)
            import time
            intent_start = time.time()
            intent = self.agent._classify_intent_llm(question, conversation_history, session.metadata)
            intent_time = time.time() - intent_start
            self.logger.info(f"Intent classification took {intent_time:.2f}s, result: {intent}")
            
            # Stream for ALL queries (not just knowledge queries)
            # For non-knowledge queries, stream directly from LLM
            if intent not in ["knowledge_query", "kg_query"]:
                # Stream directly from LLM for non-knowledge queries
                # Build messages for streaming
                messages = []
                
                # Get style/tone instructions
                style_tone_instructions = self.agent._get_style_tone_instructions(session.metadata)
                
                # Build system prompt based on intent
                if intent == "greeting":
                    system_prompt = f"""You are an enthusiastic Podcast Intelligence Assistant named Sage - a curious explorer of ideas from fascinating podcast conversations.

CRITICAL: You ONLY answer questions about podcast transcripts, knowledge graph content, and topics related to philosophy, creativity, coaching, and personal development. Do NOT answer math problems, general knowledge, or questions outside your domain.

PERSONALITY:
- Warm, intellectually curious, and genuinely excited about helping
- You love connecting dots between ideas from different thinkers
- You speak like a thoughtful friend who's passionate about learning

{style_tone_instructions}

Respond warmly and naturally to greetings. Keep it brief and inviting."""
                elif intent == "conversational":
                    system_prompt = f"""You are Sage, a warm and intellectually curious Podcast Intelligence Assistant.

CRITICAL: You ONLY answer questions about podcast transcripts, knowledge graph content, and topics related to philosophy, creativity, coaching, and personal development. Do NOT answer math problems, general knowledge, or questions outside your domain.

{style_tone_instructions}

Respond naturally to conversational queries. Be engaging and helpful."""
                else:
                    system_prompt = f"""You are Sage, a Podcast Intelligence Assistant.

CRITICAL: You ONLY answer questions about podcast transcripts, knowledge graph content, and topics related to philosophy, creativity, coaching, and personal development. Do NOT answer math problems, general knowledge, or questions outside your domain.

{style_tone_instructions}

Respond helpfully and naturally."""
                
                messages.append({"role": "system", "content": system_prompt})
                
                # Add conversation history
                if conversation_history:
                    for msg in conversation_history[-5:]:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        if role in ["user", "assistant"] and content:
                            messages.append({"role": role, "content": content})
                
                # Add current question
                messages.append({"role": "user", "content": question})
                
                # Stream response from LLM
                stream = self.agent.openai_client.chat.completions.create(
                    model=self.agent.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                    stream=True,  # Enable streaming
                )
                
                # Yield chunks as they arrive
                full_answer = ""
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            full_answer += delta.content
                            yield {"chunk": delta.content, "done": False}
                
                # Save answer to session
                if full_answer:
                    session.add_message("assistant", full_answer)
                    self._save_session_to_db(session)
                
                # Final chunk with metadata
                yield {
                    "chunk": "",
                    "done": True,
                    "session_id": session.session_id,
                    "sources": [],
                    "metadata": {"method": "agent_streaming", "type": intent}
                }
                return
            
            # Extract entities and resolve pronouns
            mentioned_entities = self.agent._extract_mentioned_entities(question)
            resolved_query = self.agent._resolve_pronouns(question, session.metadata)
            
            # Parallel RAG + KG search
            rag_results = []
            kg_results = []
            
            def _rag_search():
                if self.hybrid_retriever:
                    try:
                        return self.hybrid_retriever.retrieve(resolved_query, use_vector=True, use_graph=False), None
                    except Exception as e:
                        return [], e
                return [], None
            
            def _kg_search():
                if self.neo4j_client:
                    try:
                        # Check if Neo4j is actually connected
                        try:
                            # Quick health check
                            test_query = "RETURN 1 as test"
                            self.neo4j_client.execute_read(test_query, {})
                        except Exception as conn_error:
                            self.logger.error(f"Neo4j connection check failed: {conn_error}")
                            return [], f"Neo4j connection error: {conn_error}"
                        
                        results = self.agent._search_knowledge_graph(resolved_query)
                        return results, None
                    except Exception as e:
                        self.logger.error(f"KG search exception: {e}", exc_info=True)
                        return [], e
                else:
                    self.logger.warning("Neo4j client not available for KG search")
                    return [], None
            
            # Execute searches in parallel with timeout
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            import time
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                rag_future = executor.submit(_rag_search)
                kg_future = executor.submit(_kg_search)
                
                # Wait for RAG first (usually faster), then KG with timeout
                try:
                    rag_result, rag_error = rag_future.result(timeout=10.0)  # 10s timeout for RAG
                    rag_results = rag_result
                    self.logger.info(f"RAG search completed in {time.time() - start_time:.2f}s, returned {len(rag_results)} results")
                except FutureTimeoutError:
                    self.logger.warning("RAG search timed out after 10s")
                    rag_results = []
                    rag_error = "Timeout"
                
                # Don't wait too long for KG - start streaming if RAG is ready
                try:
                    kg_result, kg_error = kg_future.result(timeout=5.0)  # 5s timeout for KG
                    kg_results = kg_result
                    self.logger.info(f"KG search completed in {time.time() - start_time:.2f}s, returned {len(kg_results)} results")
                except FutureTimeoutError:
                    self.logger.warning("KG search timed out after 5s - proceeding without KG results")
                    kg_results = []
                    kg_error = "Timeout"
                
                # Log errors
                if rag_error:
                    self.logger.warning(f"RAG search error: {rag_error}")
                if kg_error:
                    self.logger.warning(f"KG search error: {kg_error}")
            
            # Validate entity coverage
            coverage_info = None
            if mentioned_entities and len(mentioned_entities) > 1:
                coverage_info = self.agent._validate_entity_coverage(mentioned_entities, rag_results, kg_results)
            
            # Stream answer synthesis
            full_answer = ""
            for chunk in self.agent._synthesize_answer_streaming(
                query=question,
                resolved_query=resolved_query,
                rag_results=rag_results[:5],
                kg_results=kg_results[:10],
                conversation_history=conversation_history,
                coverage_info=coverage_info,
                mentioned_entities=mentioned_entities,
                session_metadata=session.metadata,
            ):
                full_answer += chunk
                yield {"chunk": chunk, "done": False}
            
            # Extract sources
            sources = self.agent._extract_sources(rag_results[:5], kg_results[:10])
            
            # Prepare metadata with sources, rag_count, and kg_count
            message_metadata = {
                "method": "agent_streaming",
                "tools_used": ["search_transcripts", "search_knowledge_graph"],
                "rag_count": len(rag_results),
                "kg_count": len(kg_results),
                "sources": sources,  # Include sources in metadata for persistence
            }
            
            # Debug logging
            self.logger.info(
                "saving_message_with_metadata",
                extra={
                    "context": {
                        "session_id": session.session_id,
                        "rag_count": message_metadata["rag_count"],
                        "kg_count": message_metadata["kg_count"],
                        "sources_count": len(sources),
                        "metadata_keys": list(message_metadata.keys())
                    }
                }
            )
            
            # Save complete answer to session with metadata
            if full_answer:
                # Add message with metadata - ensure it's a proper dict
                if not isinstance(message_metadata, dict):
                    message_metadata = dict(message_metadata) if message_metadata else {}
                
                # Add message with metadata
                session.add_message("assistant", full_answer, metadata=message_metadata)
                
                # CRITICAL: Directly set metadata on the message object to ensure it's saved
                # This is a workaround in case the Message constructor doesn't preserve metadata correctly
                last_msg = list(session.messages)[-1] if session.messages else None
                if last_msg and last_msg.role == "assistant":
                    # Force set metadata directly on the message object
                    last_msg.metadata = message_metadata.copy() if message_metadata else {}
                    
                    self.logger.info(
                        "metadata_force_set",
                        extra={
                            "context": {
                                "session_id": session.session_id,
                                "metadata_keys": list(last_msg.metadata.keys()),
                                "rag_count": last_msg.metadata.get("rag_count"),
                                "kg_count": last_msg.metadata.get("kg_count"),
                            }
                        }
                    )
                    
                    self.logger.info(
                        "message_saved_with_metadata",
                        extra={
                            "context": {
                                "has_metadata": bool(last_msg.metadata),
                                "metadata_keys": list(last_msg.metadata.keys()) if last_msg.metadata else [],
                                "rag_count": last_msg.metadata.get("rag_count") if last_msg.metadata else None,
                                "kg_count": last_msg.metadata.get("kg_count") if last_msg.metadata else None,
                                "sources_count": len(last_msg.metadata.get("sources", [])) if last_msg.metadata else 0,
                            }
                        }
                    )
                
                # Save to database
                self._save_session_to_db(session)
                
                # Verify what was saved
                messages_for_verification = [msg.to_dict() for msg in session.get_conversation_history()]
                last_msg_dict = messages_for_verification[-1] if messages_for_verification else None
                if last_msg_dict and last_msg_dict.get("role") == "assistant":
                    self.logger.info(
                        "verifying_saved_metadata",
                        extra={
                            "context": {
                                "has_metadata_in_dict": bool(last_msg_dict.get("metadata")),
                                "metadata_keys_in_dict": list(last_msg_dict.get("metadata", {}).keys()),
                                "rag_count_in_dict": last_msg_dict.get("metadata", {}).get("rag_count"),
                                "kg_count_in_dict": last_msg_dict.get("metadata", {}).get("kg_count"),
                            }
                        }
                    )
            
            # Final message with metadata
            yield {
                "chunk": "",
                "done": True,
                "session_id": session.session_id,
                "sources": sources,
                "metadata": {
                    "method": "agent_streaming",
                    "tools_used": ["search_transcripts", "search_knowledge_graph"],
                    "rag_count": len(rag_results),
                    "kg_count": len(kg_results),
                }
            }
            
        except Exception as e:
            self.logger.error(
                "query_streaming_failed",
                exc_info=True,
                extra={"context": {"question": question[:100], "error": str(e)}},
            )
            yield {"chunk": f"Error: {str(e)}", "done": True}

    def _has_sufficient_context_for_answer(
        self,
        question: str,
        conversation_history: List[Dict[str, Any]],
        intent: QueryIntent,
        intent_metadata: Dict[str, Any],
    ) -> bool:
        """
        Determine if there's enough conversational context to answer without clarification.
        
        This prevents false clarifications when:
        1. User asks about "this system" after receiving an answer
        2. User follows up after acknowledging previous answer ("ok", "ahh")
        3. Question references the system/response itself
        4. Recent conversation has substantive content
        
        RULE: Humans resolve ambiguity using context — so should we.
        """
        question_lower = question.lower().strip()
        
        # =====================================================
        # RULE 1: SYSTEM QUESTIONS ARE NEVER CLARIFIED
        # Questions about the system itself should always be answered
        # =====================================================
        system_question_patterns = [
            "what is this system",
            "how does this system work",
            "how does this work",
            "what am i talking to",
            "what are you",
            "who are you",
            "what is this",
            "explain this system",
            "what can you do",
            "what do you do",
        ]
        
        for pattern in system_question_patterns:
            if pattern in question_lower or question_lower == pattern:
                return True  # Skip clarification, answer directly
        
        # =====================================================
        # RULE 2: RECENT SUBSTANTIVE ANSWER EXISTS
        # If we just gave a detailed answer, user's follow-up has context
        # =====================================================
        if conversation_history and len(conversation_history) >= 2:
            # Look for recent assistant message with actual content
            for msg in reversed(conversation_history[-6:]):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    metadata = msg.get("metadata", {})
                    
                    # Check if it was a substantive answer (not clarification/greeting)
                    method = metadata.get("method", "")
                    if method not in ["low_confidence_clarification", "direct_greeting", "direct_non_query", "silence"]:
                        # Substantive answer exists
                        if len(content) > 100:  # Non-trivial response
                            return True
                    break
        
        # =====================================================
        # RULE 3: USER ACKNOWLEDGED PREVIOUS ANSWER
        # "ok", "ahh", "got it" followed by question = contextual follow-up
        # =====================================================
        acknowledgment_patterns = {"ok", "okay", "ahh", "ah", "got it", "i see", "makes sense", "understood", "cool", "nice", "great", "thanks"}
        
        if conversation_history and len(conversation_history) >= 2:
            # Check if previous user message was an acknowledgment
            for i, msg in enumerate(reversed(conversation_history)):
                if msg.get("role") == "user":
                    prev_user_msg = msg.get("content", "").lower().strip().rstrip("!.,")
                    if prev_user_msg in acknowledgment_patterns:
                        # User acknowledged, then asked something = contextual
                        return True
                    break  # Only check the most recent user message before current
        
        # =====================================================
        # RULE 4: QUESTION REFERENCES RESPONSE/CONTEXT
        # "this", "that", "it" when we have active_entity or recent answer
        # =====================================================
        reference_words = {"this", "that", "it", "these", "those"}
        words = set(question_lower.split())
        
        if words & reference_words:
            # Has reference word - check if we have context to resolve it
            if intent_metadata.get("resolved_entity"):
                return True
            # Check for active entity in session
            # (This is passed via intent_metadata from session.metadata)
            if intent_metadata.get("entities"):
                return True
        
        # =====================================================
        # RULE 5: FOLLOW_UP INTENT WITH CONTEXT
        # If classifier already determined it's a follow-up, trust it
        # =====================================================
        if intent == QueryIntent.FOLLOW_UP and conversation_history:
            return True
        
        # Default: No special context, allow clarification if needed
        return False

    def _extract_entity_from_question(self, question: str) -> Optional[str]:
        """
        Extract the primary entity/subject from a question.
        
        Simple pattern-based extraction for common question formats:
        - "Who is X?" → X
        - "What is X?" → X
        - "Tell me about X" → X
        - "What does X think about..." → X
        """
        import re
        question_lower = question.lower().strip()
        
        # Pattern: "Who is X?" or "Who was X?"
        match = re.search(r"who (?:is|was|are|were) ([^?]+)", question_lower)
        if match:
            return match.group(1).strip().title()
        
        # Pattern: "What is X?" (but not "What is this/that/it")
        match = re.search(r"what (?:is|are) ([^?]+)", question_lower)
        if match:
            entity = match.group(1).strip()
            if entity not in {"this", "that", "it", "this?", "that?", "it?"}:
                return entity.title()
        
        # Pattern: "Tell me about X"
        match = re.search(r"tell me about ([^?]+)", question_lower)
        if match:
            return match.group(1).strip().title()
        
        # Pattern: "What does X think/say/believe..."
        match = re.search(r"what (?:does|did) ([a-z\s]+) (?:think|say|believe|mean)", question_lower)
        if match:
            return match.group(1).strip().title()
        
        return None

    def _query_with_llm(self, question: str, session: QuerySession) -> Dict[str, Any]:
        """Query using LLM chain."""
        context = {
            "conversation_history": [
                msg.to_dict() for msg in session.get_conversation_history(max_messages=5)
            ],
        }
        
        result = self.cypher_chain.query(question, context=context)
        
        return {
            "answer": result.get("answer", ""),
            "intermediate_steps": result.get("intermediate_steps", []),
            "metadata": {"method": "llm"},
        }
    
    def _query_with_hybrid(
        self, 
        question: str, 
        session: QuerySession,
        intent: Optional[QueryIntent] = None,
        intent_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query using hybrid RAG + KG approach.
        
        ENHANCED: Now receives intent information from the classifier to make
        smarter decisions about how to process the query.
        """
        # SPECIAL CASE: KG_META_EXPLORE - List/explore KG contents directly
        if intent == QueryIntent.KG_META_EXPLORE:
            return self._handle_kg_meta_explore(question, session)
        
        # Build context for query generator
        conversation_history = [
            msg.to_dict() for msg in session.get_conversation_history(max_messages=10)
        ] if session else []
        context = {"conversation_history": conversation_history}
        
        # If this is a FOLLOW_UP with a resolved entity, modify the question
        resolved_entity = intent_metadata.get("resolved_entity") if intent_metadata else None
        if resolved_entity and intent == QueryIntent.FOLLOW_UP:
            # Enhance the question with the resolved entity for better search
            question = f"{question} (referring to: {resolved_entity})"
            self.logger.info(
                "question_enhanced_with_entity",
                extra={"context": {"original": question[:50], "entity": resolved_entity}}
            )
        
        # Step 1: Vector search (RAG) - get relevant text chunks
        rag_results = self.hybrid_retriever.retrieve(question, use_vector=True, use_graph=False)
        rag_context = self._format_rag_context(rag_results[:5])
        
        # Step 2: Graph search (KG) - get structured data
        kg_results = self.hybrid_retriever.retrieve(question, use_vector=False, use_graph=True)
        
        # Step 3: Generate Cypher query for detailed KG info
        # IntelligentQueryGenerator handles pronoun resolution internally
        try:
            cypher = self.query_generator.generate_cypher(question, context=context)
            detailed_kg = self.query_generator.execute_query(cypher)
        except Exception as e:
            self.logger.warning(
                "cypher_query_failed",
                extra={"context": {"error": str(e), "question": question}}
            )
            detailed_kg = []
        
        # Combine KG results from both sources
        combined_kg_results = kg_results + detailed_kg
        
        # Step 4: Check if question is out of scope (enhanced with intent info)
        # If intent classifier already marked as OUT_OF_SCOPE, trust that
        is_out_of_scope = False
        if intent == QueryIntent.OUT_OF_SCOPE:
            is_out_of_scope = True
        elif not rag_results and not combined_kg_results:
            # No results at all - likely out of scope
            is_out_of_scope = self._check_out_of_scope(question, rag_results, combined_kg_results)
        
        # Step 5: Synthesize answer using LLM
        question_lower = question.lower().strip()
        answer = None
        
        # Handle out of scope
        if is_out_of_scope:
            answer = "I don't have information about that topic in this knowledge base. This knowledge base contains information from podcast transcripts about philosophy, creativity, coaching, and personal development. Please ask questions related to these topics."
        
        if answer is None:
            # Normal answer synthesis
            if rag_context or combined_kg_results:
                answer = self._synthesize_hybrid_answer(question, rag_context, combined_kg_results, rag_results, session)
            else:
                # Fallback formatting
                answer = self._format_hybrid_results(rag_results, combined_kg_results)
        
        # Step 6: Extract sources for citation
        sources = self._extract_sources(rag_results, combined_kg_results)
        
        return {
            "answer": answer,
            "sources": sources,
            "intermediate_steps": [
                {"rag_results": rag_results[:5]},
                {"kg_results": combined_kg_results[:5]}
            ],
            "metadata": {
                "method": "hybrid",
                "rag_count": len(rag_results),
                "kg_count": len(combined_kg_results),
                "is_out_of_scope": is_out_of_scope,
            },
        }
    
    def _handle_kg_meta_explore(self, question: str, session: QuerySession) -> Dict[str, Any]:
        """
        Handle KG_META_EXPLORE intent - list/explore KG contents directly from Neo4j.
        
        This allows users to browse the knowledge graph:
        - "List all concepts"
        - "Show me the relationships"
        - "What concepts do you have?"
        """
        question_lower = question.lower()
        
        # DEBUG: Log workspace_id being used
        self.logger.info(
            "kg_meta_explore_start",
            extra={"context": {"workspace_id": self.workspace_id, "question": question[:50]}}
        )
        
        try:
            results = []
            answer_parts = []
            
            # Determine what to explore based on the question
            explore_concepts = any(word in question_lower for word in ["concept", "entity", "entities", "ideas"])
            explore_relationships = any(word in question_lower for word in ["relationship", "connection", "relation"])
            explore_all = not explore_concepts and not explore_relationships
            
            if explore_concepts or explore_all:
                # Query for concepts - get more results for better overview
                concepts_query = """
                MATCH (c)
                WHERE c.workspace_id = $workspace_id
                  AND (c:Concept OR c:Practice OR c:CognitiveState OR c:BehavioralPattern 
                       OR c:Principle OR c:Outcome OR c:Person)
                RETURN DISTINCT c.name as name, labels(c)[0] as type
                ORDER BY type(c), c.name
                LIMIT 100
                """
                
                # DEBUG: Log the query
                self.logger.info(
                    "kg_meta_explore_concepts_query",
                    extra={"context": {"workspace_id": self.workspace_id}}
                )
                
                concepts_result = self.neo4j_client.execute_read(
                    concepts_query, 
                    {"workspace_id": self.workspace_id}
                )
                
                # DEBUG: Log results count
                self.logger.info(
                    "kg_meta_explore_concepts_result",
                    extra={"context": {
                        "count": len(concepts_result) if concepts_result else 0,
                        "sample": concepts_result[:3] if concepts_result else []
                    }}
                )
                
                if concepts_result:
                    answer_parts.append("## 📚 Concepts in the Knowledge Graph\n")
                    # Group by type
                    by_type = {}
                    for r in concepts_result:
                        t = r.get("type", "Other")
                        if t not in by_type:
                            by_type[t] = []
                        by_type[t].append(r.get("name", "Unknown"))
                    
                    for t, names in sorted(by_type.items()):
                        answer_parts.append(f"\n**{t}s** ({len(names)}):")
                        for name in sorted(names)[:10]:
                            answer_parts.append(f"  • {name}")
                        if len(names) > 10:
                            answer_parts.append(f"  • ... and {len(names) - 10} more")
                    
                    results.extend(concepts_result)
            
            if explore_relationships or explore_all:
                # Query for relationship types
                rels_query = """
                MATCH (a)-[r]->(b)
                WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
                RETURN DISTINCT type(r) as relationship_type, count(*) as count
                ORDER BY count DESC
                LIMIT 20
                """
                rels_result = self.neo4j_client.execute_read(
                    rels_query,
                    {"workspace_id": self.workspace_id}
                )
                
                if rels_result:
                    answer_parts.append("\n\n## 🔗 Relationship Types\n")
                    for r in rels_result:
                        rel_type = r.get("relationship_type", "Unknown")
                        count = r.get("count", 0)
                        answer_parts.append(f"  • **{rel_type}** ({count} connections)")
                    
                    results.extend(rels_result)
            
            if not results:
                answer = "The knowledge graph is empty. Please ingest some transcripts first."
            else:
                answer = "\n".join(answer_parts)
                answer += "\n\n---\n*Ask me about any of these concepts to learn more!*"
            
            return {
                "answer": answer,
                "sources": [],
                "intermediate_steps": [{"kg_explore_results": results}],
                "metadata": {
                    "method": "kg_meta_explore",
                    "rag_count": 0,
                    "kg_count": len(results),
                },
            }
            
        except Exception as e:
            self.logger.error(
                "kg_meta_explore_failed",
                exc_info=True,
                extra={"context": {"error": str(e)}}
            )
            return {
                "answer": f"I couldn't explore the knowledge graph: {str(e)}",
                "sources": [],
                "intermediate_steps": [],
                "metadata": {"method": "kg_meta_explore", "error": str(e)},
            }

    def _format_rag_context(self, rag_results: List[Dict[str, Any]]) -> str:
        """Format RAG results into context with source information."""
        if not rag_results:
            return ""
        
        context_parts = []
        seen_episodes = set()
        
        for i, result in enumerate(rag_results, 1):
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            episode_id = metadata.get("episode_id", "unknown")
            source_path = metadata.get("source_path", "")
            timestamp = metadata.get("timestamp", "")
            speaker = metadata.get("speaker", "")
            
            # Build context with source info
            context_line = f"[Source {i}]"
            if episode_id and episode_id != "unknown":
                context_line += f" Episode: {episode_id}"
            if speaker:
                context_line += f", Speaker: {speaker}"
            if timestamp:
                context_line += f", Time: {timestamp}"
            context_line += f"\n{text}\n"
            
            context_parts.append(context_line)
            if episode_id and episode_id != "unknown":
                seen_episodes.add(episode_id)
        
        return "\n".join(context_parts)
    
    def _check_out_of_scope(self, question: str, rag_results: List[Dict[str, Any]], kg_results: List[Dict[str, Any]]) -> bool:
        """Check if question is outside the knowledge base scope."""
        # If no results at all, likely out of scope
        if not rag_results and not kg_results:
            return True
        
        # Check for common out-of-scope topics
        out_of_scope_keywords = [
            "prime minister", "president", "pakistan", "india", "country", "government",
            "current events", "news", "today", "recent", "latest", "breaking"
        ]
        question_lower = question.lower()
        if any(keyword in question_lower for keyword in out_of_scope_keywords):
            # Check if we have relevant results
            if len(rag_results) == 0 or (len(rag_results) > 0 and rag_results[0].get("score", 0) < 0.3):
                return True
        
        return False
    
    def _extract_sources(self, rag_results: List[Dict[str, Any]], kg_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source citations from results."""
        sources = []
        seen_sources = set()
        
        # Extract from RAG results
        for result in rag_results[:5]:
            metadata = result.get("metadata", {})
            episode_id = metadata.get("episode_id")
            source_path = metadata.get("source_path", "")
            timestamp = metadata.get("timestamp", "")
            
            source_key = f"{episode_id}:{source_path}"
            if source_key not in seen_sources and episode_id:
                sources.append({
                    "type": "transcript",
                    "episode_id": episode_id,
                    "source_path": source_path,
                    "timestamp": timestamp,
                })
                seen_sources.add(source_key)
        
        # Extract from KG results
        for result in kg_results[:5]:
            episode_ids = result.get("episode_ids", [])
            source_paths = result.get("source_paths", [])
            
            if isinstance(episode_ids, list):
                for ep_id in episode_ids[:3]:  # Limit to 3 per concept
                    if ep_id and ep_id not in seen_sources:
                        sources.append({
                            "type": "knowledge_graph",
                            "episode_id": ep_id,
                            "concept": result.get("name", ""),
                        })
                        seen_sources.add(ep_id)
        
        return sources
    
    def _synthesize_hybrid_answer(
        self, 
        question: str, 
        rag_context: str, 
        kg_results: List[Dict[str, Any]],
        rag_results: List[Dict[str, Any]],
        session: QuerySession = None
    ) -> str:
        """Synthesize answer from RAG + KG using LLM with improved context handling."""
        # Format KG results with more detail
        kg_text = ""
        if kg_results:
            kg_text = "Knowledge Graph Information:\n"
            for r in kg_results[:10]:  # Show more KG results
                # Try multiple fields for name
                name = r.get('name') or r.get('concept') or r.get('c.name') or r.get('n.name') or r.get('text', '')[:50]
                if not name or name == 'Unknown':
                    # Skip entries without meaningful names
                    continue
                kg_text += f"- {name}"
                # Get type from multiple possible fields
                node_type = r.get('type') or r.get('c.type') or r.get('n.type') or r.get('label')
                if node_type:
                    kg_text += f" ({node_type})"
                # Get description from multiple possible fields
                desc = r.get('description') or r.get('c.description') or r.get('n.description') or ''
                if desc:
                    kg_text += f": {desc[:200]}"
                # Add relationships if available
                rels_out = r.get('relationships_out', [])
                rels_in = r.get('relationships_in', [])
                if rels_out:
                    rel_names = [rel.get('target') for rel in rels_out if rel.get('target')][:3]
                    if rel_names:
                        kg_text += f" → relates to: {', '.join(rel_names)}"
                if rels_in:
                    rel_names = [rel.get('source') for rel in rels_in if rel.get('source')][:3]
                    if rel_names:
                        kg_text += f" ← related from: {', '.join(rel_names)}"
                # Add episode info if available
                episode_ids = r.get('episode_ids') or r.get('c.episode_ids') or []
                if episode_ids and isinstance(episode_ids, list):
                    kg_text += f" [Appears in {len(episode_ids)} episode(s)]"
                kg_text += "\n"
        
        # Build improved conversation context for pronoun and reference resolution
        conversation_context = ""
        if session:
            # Get more messages (last 10) to capture full context including numbered lists
            history = session.get_conversation_history(max_messages=10)
            if history:
                conversation_context = "\n\nPrevious Conversation Context (for resolving references like 'Point # 5', 'he', 'she', 'it', 'they', 'that', numbered lists, etc.):\n"
                for msg in history[-10:]:
                    role = "User" if msg.role == "user" else "Assistant"
                    # Include FULL content for both user and assistant messages
                    # User messages might reference specific points from earlier
                    # Assistant messages contain numbered lists that need to be resolved
                    content = msg.content  # Full content for proper reference resolution
                    conversation_context += f"{role}: {content}\n"
                conversation_context += "\nIMPORTANT: \n"
                conversation_context += "1. When the user asks about 'Point # X', 'Item # X', numbered lists, etc., look at the previous Assistant messages to find the numbered list and identify what they're referring to.\n"
                conversation_context += "2. When the user asks about 'he', 'she', 'it', 'they', 'that', 'this', etc., look at the previous conversation to identify what they're referring to.\n"
                conversation_context += "3. Always use the full context from previous messages to understand references.\n"
        
        # Enhanced prompt with better structure and PRESENTATION FILTERING
        prompt = f"""You are answering questions about podcast transcripts containing discussions on philosophy, creativity, coaching, and personal development.

Question: {question}
{conversation_context}

Relevant Text from Transcripts:
{rag_context if rag_context else "No relevant text found."}

Knowledge Graph Information (structured concepts and relationships):
{kg_text if kg_text else "No graph information found."}

Instructions:
1. Answer the question using BOTH the text context and knowledge graph information
2. CRITICAL: If the question references numbered items (e.g., "Point # 5", "Item # 3", "the first point"), look at the previous conversation context to find what that numbered item was about, and answer based on that specific point.
3. If the question uses pronouns (he, she, it, that, they, etc.), use the previous conversation context to identify what they refer to
4. If the question references "the first one", "the last point", "that idea", etc., use the conversation context to identify what they're referring to
5. Be comprehensive but concise
6. If you're not certain about something, say so rather than guessing

**SOURCE CITATION RULES (IMPORTANT):**
- Cite sources NATURALLY within your answer, not at the end
- Use phrases like "According to [Speaker Name]...", "In Episode [X], [Speaker] explains...", "[Speaker Name] suggests that..."
- Integrate citations into the flow of your response
- Don't just list sources at the end - weave them into the narrative

GOOD: "Phil Jackson emphasizes the importance of mindfulness in leadership. He describes how meditation helped his teams stay focused under pressure."
BAD: "Mindfulness is important in leadership. [Sources: Phil Jackson, Episode 42]"

**PRESENTATION RULES (MUST FOLLOW):**
- DO NOT explain how you resolved references
- DO NOT narrate your reasoning process
- DO NOT remind the user what they asked
- JUST ANSWER DIRECTLY with the content itself
- Start your answer with the actual information, not meta-commentary

Provide your answer:"""

        try:
            from openai import OpenAI
            import os
            from dotenv import load_dotenv
            load_dotenv()
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            # Use the model from initialization (defaults to gpt-4o for better reasoning)
            response = client.chat.completions.create(
                model=self.model,  # Use configured model (gpt-4o for better reasoning)
                temperature=0.6,  # Higher temperature for natural, varied conversational responses
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert AI assistant with deep understanding of podcast content on philosophy, creativity, coaching, and personal development. 

Your capabilities:
- You maintain full conversation context and resolve ALL references (pronouns, numbered items like 'Point # 5', 'the first one', etc.) based on previous messages
- You synthesize information from both text context (RAG) and knowledge graph (structured relationships)
- You provide evidence-grounded, accurate answers with natural source citations
- You think critically and reason through complex questions using multi-hop reasoning
- You are comprehensive yet concise, always prioritizing accuracy over speculation

CRITICAL INSTRUCTIONS:
1. ALWAYS check previous conversation context to resolve ANY references (pronouns, numbered items, "that", "this", etc.)
2. Use BOTH text context AND knowledge graph relationships to form complete answers
3. If uncertain, state your uncertainty rather than guessing
4. Cite sources naturally when mentioning specific information
5. For vague questions, infer the most likely intent based on conversation context

**PRESENTATION RULES (MANDATORY):**
- NEVER explain how you understood the question
- NEVER narrate your reasoning process to the user
- NEVER say things like "You asked about X" or "Let me clarify"
- NEVER describe reference resolution steps
- JUST PROVIDE THE ANSWER DIRECTLY
- Start with the actual content, not meta-commentary
- Sound like a knowledgeable human, not a verbose AI"""
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content
            
            # Append source citations if available
            sources = self._extract_sources(rag_results, kg_results)
            if sources:
                episode_ids = list(set([s.get("episode_id") for s in sources if s.get("episode_id")]))[:3]
                if episode_ids:
                    answer += f"\n\n[Sources: {', '.join(episode_ids)}]"
            
            return answer
        except Exception as e:
            self.logger.warning("llm_synthesis_failed", extra={"error": str(e)})
            return self._format_hybrid_results(rag_results, kg_results)
    
    def _format_hybrid_results(
        self, 
        rag_results: List[Dict[str, Any]], 
        kg_results: List[Dict[str, Any]]
    ) -> str:
        """Format hybrid results without LLM."""
        parts = []
        
        if kg_results:
            parts.append("Knowledge Graph Results:")
            for r in kg_results[:5]:
                name = r.get('name') or r.get('concept') or r.get('c.name') or r.get('n.name') or r.get('text', '')[:50] or 'Unknown'
                parts.append(f"- {name}")
                if r.get('type'):
                    parts[-1] += f" ({r['type']})"
                if r.get('description'):
                    parts.append(f"  {r['description']}")
        
        if rag_results:
            parts.append("\nRelevant Text:")
            for r in rag_results[:2]:
                text = r.get('text', '')[:200]
                if text:
                    parts.append(f"- {text}...")
        
        return "\n".join(parts) if parts else "No results found."
        
    def _query_with_patterns(self, question: str, session: QuerySession) -> Dict[str, Any]:
        """
        Query using pattern matching.
        
        NOTE: Greetings and conversational responses are now handled by the
        IntentClassifier BEFORE reaching this method.
        """
        # Generate Cypher query
        try:
            cypher = self.query_generator.generate_cypher(question)
            
            # Execute query
            results = self.query_generator.execute_query(cypher)
            
            # Format results
            if not results:
                answer = "No results found for your query. Try asking about:\n- Concepts in the knowledge graph\n- Practices and their effects\n- Quotes from the transcripts\n- Relationships between concepts"
            else:
                answer = self._format_results(results)
            
            return {
                "answer": answer,
                "intermediate_steps": [{"cypher": cypher, "results": results}],
                "metadata": {"method": "pattern", "result_count": len(results)},
            }
        except Exception as e:
            self.logger.error(
                "pattern_query_failed",
                exc_info=True,
                extra={"context": {"question": question[:100], "error": str(e)}},
            )
            return {
                "answer": f"I encountered an error processing your query: {str(e)}\n\nTry asking simpler questions about concepts, practices, or quotes in the knowledge graph.",
                "intermediate_steps": [],
                "metadata": {"method": "error"},
            }

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format query results as text."""
        if not results:
            return "No results found."
        
        # Special formatting for entity lookup queries
        if len(results) == 1 and "name" in results[0] and "relationships" in results[0]:
            result = results[0]
            formatted = [f"**{result.get('name', 'Unknown')}**"]
            
            if result.get("type"):
                formatted.append(f"Type: {result['type']}")
            
            if result.get("description"):
                formatted.append(f"Description: {result['description']}")
            
            if result.get("episodes"):
                formatted.append(f"Appears in {len(result['episodes'])} episode(s)")
            
            # Format relationships
            relationships_out = result.get("relationships_out", [])
            relationships_in = result.get("relationships_in", [])
            
            if relationships_out:
                formatted.append("\nRelationships:")
                for rel in relationships_out[:5]:
                    if rel.get("rel") and rel.get("target"):
                        formatted.append(f"  - {rel['rel']} → {rel['target']}")
            
            if relationships_in:
                formatted.append("\nRelated from:")
                for rel in relationships_in[:5]:
                    if rel.get("rel") and rel.get("source"):
                        formatted.append(f"  - {rel['source']} {rel['rel']} →")
            
            return "\n".join(formatted)
        
        # Default formatting
        formatted = []
        for i, result in enumerate(results[:10], 1):  # Limit to 10 results
            parts = []
            for key, value in result.items():
                if value is not None and key not in ["relationships", "relationships_out", "relationships_in"]:
                    # Format lists/arrays
                    if isinstance(value, list):
                        if value:
                            parts.append(f"{key}: {', '.join(map(str, value[:3]))}{'...' if len(value) > 3 else ''}")
                    else:
                        parts.append(f"{key}: {value}")
            formatted.append(f"{i}. " + " | ".join(parts))
        
        return "\n".join(formatted)

    def get_session(self, session_id: str) -> Optional[QuerySession]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            QuerySession if found, None otherwise
        """
        return self.session_manager.get_session(session_id)

    def create_session(self, session_id: Optional[str] = None) -> QuerySession:
        """
        Create a new session.

        Args:
            session_id: Optional session ID

        Returns:
            New QuerySession
        """
        return self.session_manager.create_session(session_id=session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted
        """
        return self.session_manager.delete_session(session_id)

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Memory statistics
        """
        return self.session_manager.get_memory_usage()

    def cleanup_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        return self.session_manager.cleanup_expired_sessions()

    def _save_session_to_db(self, session: QuerySession) -> None:
        """Save session to database for persistence across requests."""
        if not hasattr(self.session_manager, 'session_db') or not self.session_manager.session_db:
            return
        
        try:
            import json
            import sqlite3
            from pathlib import Path
            
            # Get database path from SessionDB
            db = self.session_manager.session_db
            db_path = db.db_path
            
            # Convert session messages to format expected by SessionDB
            messages_for_db = []
            for msg in session.get_conversation_history():
                msg_dict = msg.to_dict()
                # Ensure metadata is included (defensive check)
                if not msg_dict.get("metadata"):
                    msg_dict["metadata"] = msg.metadata if hasattr(msg, 'metadata') else {}
                messages_for_db.append(msg_dict)
            
            # Debug: Log what we're about to save
            if messages_for_db:
                last_msg = messages_for_db[-1]
                if last_msg.get("role") == "assistant":
                    self.logger.info(
                        "saving_to_db_with_metadata",
                        extra={
                            "context": {
                                "session_id": session.session_id,
                                "has_metadata": bool(last_msg.get("metadata")),
                                "metadata_keys": list(last_msg.get("metadata", {}).keys()),
                                "rag_count": last_msg.get("metadata", {}).get("rag_count"),
                                "kg_count": last_msg.get("metadata", {}).get("kg_count"),
                            }
                        }
                    )
            
            # Save entire session at once (INSERT OR REPLACE)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO sessions 
                (session_id, workspace_id, messages, metadata, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                session.session_id,
                session.workspace_id,
                json.dumps(messages_for_db, default=str),
                json.dumps(session.metadata or {}, default=str)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.warning("session_save_to_db_failed", extra={
                "context": {"session_id": session.session_id, "error": str(e)}
            })
    
    def close(self) -> None:
        """Close connections and cleanup."""
        # Save all active sessions to database before closing
        if hasattr(self.session_manager, 'session_db') and self.session_manager.session_db:
            for session_id, session in self.session_manager.sessions.items():
                try:
                    self._save_session_to_db(session)
                except Exception as e:
                    self.logger.warning("session_save_on_close_failed", extra={
                        "context": {"session_id": session_id, "error": str(e)}
                    })
        
        if self.cypher_chain:
            self.cypher_chain.close()
        
        if self.hybrid_retriever:
            self.hybrid_retriever.close()
        
        if self._owns_client:
            self.neo4j_client.close()
        
        self.logger.info("kg_reasoner_closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function
def create_reasoner(
    workspace_id: Optional[str] = None,
    use_llm: bool = True,
    use_hybrid: bool = True,
) -> KGReasoner:
    """
    Create a KG reasoner (convenience function).

    Args:
        workspace_id: Workspace identifier
        use_llm: Whether to use LLM
        use_hybrid: Whether to use hybrid retrieval

    Returns:
        KGReasoner instance
    """
    return KGReasoner(
        workspace_id=workspace_id,
        use_llm=use_llm,
        use_hybrid=use_hybrid,
    )

