"""
Intelligent Query Planner - Context-aware, domain-aware query analysis.

This planner understands:
- Context (follow-up vs new questions)
- Domain relevance (rejects irrelevant queries)
- Complexity (simple/moderate/complex)
- When to decompose queries
- Retrieval strategy planning
"""
from typing import Dict, Any, List, Optional, Literal
import json
import re
from openai import OpenAI
from core_engine.logging import get_logger
from core_engine.reasoning.langgraph_state import QueryPlan


logger = get_logger(__name__)


class IntelligentQueryPlanner:
    """
    Intelligent query planner that:
    - Understands context (session, conversation)
    - Checks domain relevance
    - Assesses complexity
    - Plans retrieval strategy
    """
    
    # Out-of-scope patterns (fast path - no LLM needed)
    OUT_OF_SCOPE_PATTERNS = [
        r"\b(calculate|math|equation|solve|algebra|geometry|trigonometry|calculus)\b",
        r"(\d+\s*[+\-*/]\s*\d+|x\s*[=+\-*/]|solve for x|what is x\s*\?|find x)",
        r"\b(code|programming|function|variable|class|import|def |print\(|if __name__)\b",
        r"\b(weather|temperature|forecast|rain|snow)\b",
        r"\b(stock|price|market|trading|bitcoin|crypto)\b",
        r"\b(current events|news|today|yesterday|recent)\b",
    ]
    
    # Simple query patterns (fast path - no LLM needed)
    SIMPLE_GREETING_PATTERNS = [
        r"^(hi|hello|hey|thanks|thank you|bye|goodbye)\s*[!.]?$",
    ]
    
    def __init__(self, openai_client: OpenAI):
        self.llm = openai_client
        self.logger = get_logger(__name__)
    
    def plan(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """
        Create intelligent query plan.
        
        Args:
            query: User query
            conversation_history: Previous messages
            session_metadata: Session context (entities, user info)
        
        Returns:
            QueryPlan with all analysis
        """
        # Step 1: Context Analysis
        context_analysis = self._analyze_context(query, conversation_history, session_metadata)
        
        # Step 1.5: FAST PATH - Check for greetings FIRST (before domain relevance)
        # Greetings don't need domain relevance check - they're always allowed
        query_lower = query.lower().strip()
        for pattern in self.SIMPLE_GREETING_PATTERNS:
            if re.match(pattern, query_lower):
                return QueryPlan(
                    is_follow_up=context_analysis["is_follow_up"],
                    is_relevant=True,  # Greetings are always relevant
                    complexity="simple",
                    intent="greeting",
                    needs_decomposition=False,
                    sub_queries=[query],
                    entities=[],
                    retrieval_strategy={
                        "use_rag": False,
                        "use_kg": False,
                        "direct_answer": True
                    }
                )
        
        # Step 2: Domain Relevance Check (with fast paths)
        relevance_check = self._check_domain_relevance(query, context_analysis)
        
        if not relevance_check["is_relevant"]:
            return QueryPlan(
                is_follow_up=context_analysis["is_follow_up"],
                is_relevant=False,
                rejection_reason=relevance_check["reason"],
                complexity="simple",
                intent="out_of_scope",
                needs_decomposition=False,
                sub_queries=[],
                entities=[],
                retrieval_strategy={}
            )
        
        # Step 3: Complexity Assessment (with fast paths)
        complexity_analysis = self._assess_complexity(query, context_analysis)
        
        # Step 4: Create Plan
        if complexity_analysis["complexity"] == "simple":
            return self._create_simple_plan(query, context_analysis, complexity_analysis)
        else:
            return self._create_complex_plan(query, context_analysis, complexity_analysis)
    
    def _analyze_context(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]],
        session_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze conversation context."""
        if not conversation_history or len(conversation_history) == 0:
            return {
                "is_follow_up": False,
                "referenced_entities": [],
                "context_summary": "",
                "previous_topics": []
            }
        
        # Analyze last few messages
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        
        # Fast path: Check for obvious follow-up indicators
        query_lower = query.lower().strip()
        follow_up_indicators = [
            "this", "that", "it", "these", "those", "he", "she", "they",
            "tell me more", "what about", "how about", "also", "and",
            "what did", "what does", "explain", "elaborate"
        ]
        
        is_follow_up_fast = any(indicator in query_lower for indicator in follow_up_indicators)
        
        # Extract entities from session metadata
        referenced_entities = []
        if session_metadata:
            active_entity = session_metadata.get("active_entity")
            if active_entity:
                referenced_entities.append(active_entity)
        
        # Use LLM for deeper context analysis if needed
        if is_follow_up_fast or len(recent_messages) > 0:
            try:
                context_prompt = f"""
                Analyze if this query is a follow-up to previous conversation.
                
                Previous messages (last 3):
                {self._format_messages(recent_messages)}
                
                Current query: {query}
                
                Determine:
                1. Is this a follow-up question? (references previous answer)
                2. What entities/concepts from previous messages are referenced?
                3. What's the conversation context summary?
                
                Return JSON:
                {{
                    "is_follow_up": bool,
                    "referenced_entities": [...],
                    "context_summary": "...",
                    "previous_topics": [...]
                }}
                """
                
                response = self.llm.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": context_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0  # Zero for deterministic classification
                )
                
                analysis = json.loads(response.choices[0].message.content)
                
                # Merge with session metadata entities
                if session_metadata:
                    active_entity = session_metadata.get("active_entity")
                    if active_entity and active_entity not in analysis.get("referenced_entities", []):
                        analysis["referenced_entities"].append(active_entity)
                
                return analysis
            except Exception as e:
                logger.warning(
                    "context_analysis_failed",
                    extra={"context": {"error": str(e), "query": query[:50]}}
                )
                # Fallback to fast path
                return {
                    "is_follow_up": is_follow_up_fast,
                    "referenced_entities": referenced_entities,
                    "context_summary": "",
                    "previous_topics": []
                }
        
        return {
            "is_follow_up": is_follow_up_fast,
            "referenced_entities": referenced_entities,
            "context_summary": "",
            "previous_topics": []
        }
    
    def _check_domain_relevance(
        self,
        query: str,
        context_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if query is relevant to podcast domain."""
        query_lower = query.lower()
        
        # Fast path: Check for obvious out-of-scope patterns
        for pattern in self.OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return {
                    "is_relevant": False,
                    "reason": "This question is outside the podcast domain (math/coding/general knowledge). I can only answer questions about podcast content."
                }
        
        # LLM-based relevance check (for nuanced cases)
        try:
            relevance_prompt = f"""
            You are a Podcast Intelligence Assistant. You ONLY answer questions about:
            - Podcast transcripts and content
            - Concepts, people, and ideas SPECIFICALLY from podcasts
            - What speakers said in podcasts
            - Practices, outcomes, relationships from podcast knowledge graph
            
            You CANNOT answer:
            - Math problems
            - Coding questions
            - Current events/news
            - General knowledge questions (even if about philosophy, creativity, etc.)
            - Questions about society, history, science, etc. unless SPECIFICALLY asking what podcast speakers said
            - Weather, sports, etc.
            
            CRITICAL RULE: A question is ONLY relevant if it:
            1. Specifically asks about podcast content ("What did X say?", "What is in the podcasts?", "What concepts are in the knowledge graph?")
            2. OR asks about concepts/people that exist in the podcast knowledge base ("What is creativity?" - if creativity is in KG)
            3. OR asks about relationships from podcasts ("What practices lead to X?" - if X is in podcasts)
            
            A question is NOT relevant if it:
            - Asks general knowledge questions ("What are main issues of society?" - general question, not about podcasts)
            - Asks about topics without referencing podcasts ("What is philosophy?" - general question)
            - Could be answered from general knowledge without podcast content
            
            Examples:
            - "What did Phil Jackson say about meditation?" - RELEVANT (asks about podcast content)
            - "What is meditation?" - RELEVANT ONLY if meditation is in podcast knowledge base
            - "What are main issues of society?" - NOT RELEVANT (general knowledge question)
            - "What is 2+2?" - NOT RELEVANT (math)
            - "What concepts are in the podcasts?" - RELEVANT (asks about podcast content)
            
            Query: {query}
            
            Previous context: {context_analysis.get('context_summary', 'None')}
            
            Determine if this query SPECIFICALLY asks about podcast content or knowledge graph.
            If it's a general knowledge question that doesn't reference podcasts, mark as NOT RELEVANT.
            
            Return JSON:
            {{
                "is_relevant": bool,
                "reason": "explanation",
                "confidence": 0.0-1.0
            }}
            """
            
            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": relevance_prompt}],
                response_format={"type": "json_object"},
                temperature=0.0  # Zero for deterministic classification
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.warning(
                "relevance_check_failed",
                extra={"context": {"error": str(e), "query": query[:50]}}
            )
            # CRITICAL FIX: Default to NOT RELEVANT if check fails (safer)
            # This prevents general knowledge questions from being marked as relevant
            return {
                "is_relevant": False,
                "reason": "Relevance check failed. I can only answer questions about podcast content.",
                "confidence": 0.0
            }
    
    def _assess_complexity(
        self,
        query: str,
        context_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess query complexity."""
        query_lower = query.lower().strip()
        
        # Fast path: Simple queries
        for pattern in self.SIMPLE_GREETING_PATTERNS:
            if re.match(pattern, query_lower):
                return {
                    "complexity": "simple",
                    "intent": "greeting",
                    "needs_decomposition": False,
                    "entities": [],
                    "relationships": []
                }
        
        # Simple definition pattern
        simple_def_pattern = r"^(what is|who is|define)\s+\w+\s*\?$"
        if re.match(simple_def_pattern, query_lower):
            return {
                "complexity": "simple",
                "intent": "definition",
                "needs_decomposition": False,
                "entities": [],
                "relationships": []
            }
        
        # LLM-based complexity assessment
        try:
            complexity_prompt = f"""
            Analyze query complexity and intent.
            
            Query: {query}
            Context: {context_analysis.get('context_summary', 'None')}
            
            Complexity levels:
            - SIMPLE: Greeting, single entity definition, yes/no
            - MODERATE: Comparison, multi-entity, causal (single hop)
            - COMPLEX: Multi-part, multi-hop causal, cross-episode analysis
            
            Intent types:
            - greeting: Only for greetings like "hi", "hello", "thanks"
            - definition: Questions asking "what is X?" about concepts
            - comparison: Questions comparing entities
            - causal: Questions about relationships/causes
            - multi_entity: Questions about multiple entities
            - cross_episode: Questions spanning episodes
            - follow_up: Follow-up questions
            - knowledge_query: Default for any knowledge question
            
            CRITICAL RULES:
            - If query asks "what is X?", "who is X?", "how does X work?", etc., intent MUST be "knowledge_query" or "definition", NOT "conversational"
            - "conversational" is ONLY for casual chat like "hmm", "ok", "thanks", NOT for questions
            - Questions that require knowledge from podcasts MUST be "knowledge_query" or "definition"
            
            Return JSON:
            {{
                "complexity": "simple" | "moderate" | "complex",
                "intent": "...",
                "needs_decomposition": bool,
                "entities": [...],
                "relationships": [...]
            }}
            """
            
            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": complexity_prompt}],
                response_format={"type": "json_object"},
                temperature=0.0  # Zero for deterministic classification
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.warning(
                "complexity_assessment_failed",
                extra={"context": {"error": str(e), "query": query[:50]}}
            )
            # Default to moderate complexity
            return {
                "complexity": "moderate",
                "intent": "knowledge_query",
                "needs_decomposition": False,
                "entities": [],
                "relationships": []
            }
    
    def _create_simple_plan(
        self,
        query: str,
        context_analysis: Dict[str, Any],
        complexity_analysis: Dict[str, Any]
    ) -> QueryPlan:
        """Create plan for simple queries (fast path)."""
        
        # For greetings, no retrieval needed
        if complexity_analysis["intent"] == "greeting":
            return QueryPlan(
                is_follow_up=context_analysis["is_follow_up"],
                is_relevant=True,
                complexity="simple",
                intent="greeting",
                needs_decomposition=False,
                sub_queries=[query],
                entities=complexity_analysis.get("entities", []),
                retrieval_strategy={
                    "use_rag": False,
                    "use_kg": False,
                    "direct_answer": True
                }
            )
        
        # For simple definitions, basic retrieval
        return QueryPlan(
            is_follow_up=context_analysis["is_follow_up"],
            is_relevant=True,
            complexity="simple",
            intent=complexity_analysis["intent"],
            needs_decomposition=False,
            sub_queries=[query],
            entities=complexity_analysis.get("entities", []),
            retrieval_strategy={
                "use_rag": True,
                "use_kg": True,
                "kg_query_type": "entity_centric",
                "rag_expansion": False,
                "iterative": False
            }
        )
    
    def _create_complex_plan(
        self,
        query: str,
        context_analysis: Dict[str, Any],
        complexity_analysis: Dict[str, Any]
    ) -> QueryPlan:
        """Create plan for complex queries."""
        
        # Decompose query
        decomposition = self._decompose_query(query, complexity_analysis)
        
        # Determine retrieval strategy
        strategy = self._determine_retrieval_strategy(complexity_analysis, decomposition)
        
        return QueryPlan(
            is_follow_up=context_analysis["is_follow_up"],
            is_relevant=True,
            complexity=complexity_analysis["complexity"],
            intent=complexity_analysis["intent"],
            needs_decomposition=True,
            sub_queries=decomposition["sub_queries"],
            entities=decomposition["entities"],
            retrieval_strategy=strategy
        )
    
    def _decompose_query(
        self,
        query: str,
        complexity_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decompose complex query into sub-queries."""
        
        intent = complexity_analysis["intent"]
        entities = complexity_analysis.get("entities", [])
        
        # Pattern-based decomposition for common cases
        if intent == "comparison":
            # "How do X and Y differ?" → ["What is X?", "What is Y?"]
            sub_queries = [f"What is {entity}?" for entity in entities]
            sub_queries.append(query)  # Also keep original for comparison
        elif intent == "multi_entity":
            # "What do X, Y, Z have in common?" → separate queries for each
            sub_queries = [f"Tell me about {entity}" for entity in entities]
            sub_queries.append(query)  # Also keep original
        elif intent == "causal":
            # "What leads to X?" → ["What is X?", "What causes X?"]
            sub_queries = [query, f"What causes {query}?"]
        else:
            # Use LLM for decomposition
            try:
                decomposition_prompt = f"""
                Decompose this complex query into sub-queries.
                
                Query: {query}
                Intent: {intent}
                Entities: {entities}
                
                Create 2-4 sub-queries that together answer the original query.
                
                Return JSON:
                {{
                    "sub_queries": [...],
                    "entities": [...],
                    "relationships": [...]
                }}
                """
                
                response = self.llm.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": decomposition_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0  # Zero for deterministic classification
                )
                
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.warning(
                    "query_decomposition_failed",
                    extra={"context": {"error": str(e), "query": query[:50]}}
                )
                # Fallback: use original query
                return {
                    "sub_queries": [query],
                    "entities": entities,
                    "relationships": complexity_analysis.get("relationships", [])
                }
        
        return {
            "sub_queries": sub_queries,
            "entities": entities,
            "relationships": complexity_analysis.get("relationships", [])
        }
    
    def _determine_retrieval_strategy(
        self,
        complexity_analysis: Dict[str, Any],
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine optimal retrieval strategy."""
        
        intent = complexity_analysis["intent"]
        entities = decomposition.get("entities", [])
        
        strategy = {
            "use_rag": True,
            "use_kg": True,
            "rag_expansion": (
                complexity_analysis["complexity"] in ["moderate", "complex"] or
                len(entities) > 1 or
                intent in ["multi_entity", "causal", "comparison"]
            ),  # Expand for moderate/complex queries, multi-entity, or relationship queries
            "iterative": complexity_analysis["complexity"] == "complex"
        }
        
        # KG query type based on intent
        if intent == "multi_entity" or len(entities) > 1:
            strategy["kg_query_type"] = "multi_hop"
        elif intent == "causal":
            strategy["kg_query_type"] = "multi_hop"  # Need to traverse relationships
        elif intent == "cross_episode":
            strategy["kg_query_type"] = "cross_episode"
        else:
            strategy["kg_query_type"] = "entity_centric"
        
        return strategy
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for context."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]  # Truncate
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
