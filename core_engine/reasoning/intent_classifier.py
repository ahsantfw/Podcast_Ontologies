"""
INTELLIGENT INTENT CLASSIFIER
Understands user intent BEFORE deciding whether to search RAG/KG or respond directly.

This is the brain of the query understanding engine - it classifies user queries into:
1. GREETING - Simple greetings like "Hi", "Hello", "Hey"
2. SYSTEM_INFO - Questions about the system itself ("What can you do?", "Who are you?")
3. KNOWLEDGE_QUERY - Questions requiring RAG/KG search ("What is meditation?")
4. RELATIONSHIP_QUERY - Questions about relationships ("How does X relate to Y?")
5. CONVERSATIONAL - Casual conversation ("Thanks", "Got it", "Interesting")
6. CLARIFICATION - User needs clarification or is confused
7. FOLLOW_UP - Follow-up on previous conversation ("Tell me more", "What about the first one?")
8. OUT_OF_SCOPE - Questions clearly outside the knowledge domain
9. NON_QUERY - Not a question at all (e.g., "ok", "hmm", "are you mad?")
10. AMBIGUOUS_REFERENCE - Deictic queries with no clear referent ("What is this?" with no context)
11. KG_META_EXPLAIN - Questions about the KG structure (explanation)
12. KG_META_EXPLORE - Requests to list/explore KG contents (needs Neo4j query)

KEY FEATURE: Entity Focus Tracking
- Tracks the "active entity" being discussed (e.g., "Phil Jackson")
- Resolves deictic references ("he", "this", "that") to the active entity
- Enables natural follow-up questions without re-stating the subject
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import os
import json
from dotenv import load_dotenv

from core_engine.logging import get_logger

load_dotenv()


class QueryIntent(Enum):
    """Classification of user query intent."""
    GREETING = "greeting"
    SYSTEM_INFO = "system_info"
    KNOWLEDGE_QUERY = "knowledge_query"
    RELATIONSHIP_QUERY = "relationship_query"
    CONVERSATIONAL = "conversational"
    CLARIFICATION = "clarification"
    FOLLOW_UP = "follow_up"
    OUT_OF_SCOPE = "out_of_scope"
    NON_QUERY = "non_query"  # Not a question - "ok", "hmm", "are you mad?"
    AMBIGUOUS_REFERENCE = "ambiguous_reference"  # Deictic with no referent - "what is this?"
    KG_META_EXPLAIN = "kg_meta_explain"  # Explain KG structure - "what are concepts?"
    KG_META_EXPLORE = "kg_meta_explore"  # List/explore KG contents - "list all concepts"
    UNKNOWN = "unknown"


class IntentClassifier:
    """
    Intelligent intent classifier using LLM for deep understanding.
    
    This classifier understands the TRUE intent behind user queries,
    not just pattern matching. It considers:
    - The actual meaning of the query
    - Conversation context
    - The knowledge domain (podcasts on philosophy, creativity, coaching)
    """

    # System introduction for different scenarios
    SYSTEM_INTRO = """Hello! I'm your **Podcast Intelligence Assistant** 🎙️

I'm an AI-powered knowledge system that helps you explore insights from podcast transcripts on:
- 🧠 **Philosophy** - Deep thinking, wisdom, mental models
- 🎨 **Creativity** - Innovation, artistic process, creative practices
- 🏆 **Coaching** - Leadership, performance, personal development
- 🧘 **Mindfulness** - Meditation, awareness, cognitive states

**What I can do:**
- Answer questions about concepts, people, and ideas from the podcasts
- Find relationships between different concepts
- Retrieve relevant quotes and their sources
- Help you discover patterns across multiple episodes

**Try asking me:**
- "What is creativity?"
- "How does meditation relate to decision-making?"
- "What practices improve focus?"
- "Who is Phil Jackson?"

How can I help you explore today?"""

    GREETING_RESPONSES = [
        "Hello! 👋 I'm your Podcast Intelligence Assistant. I can help you explore insights from podcasts on philosophy, creativity, coaching, and personal development. What would you like to know?",
        "Hi there! 🎙️ I'm here to help you discover knowledge from podcast transcripts. Ask me about concepts, relationships, quotes, or people mentioned in the podcasts!",
        "Hey! 👋 Ready to explore some fascinating ideas? I can answer questions about philosophy, creativity, coaching, and mindfulness from our podcast knowledge base.",
    ]

    CONVERSATIONAL_RESPONSES = {
        "thanks": "You're welcome! 😊 Feel free to ask if you have more questions about the podcasts.",
        "thank you": "You're welcome! Let me know if you'd like to explore more topics.",
        "got it": "Great! Let me know if you want to dive deeper into any topic.",
        "interesting": "I'm glad you find it interesting! Would you like to explore related concepts?",
        "cool": "Thanks! There's a lot more to discover. What else would you like to know?",
        "nice": "Glad you liked it! Want to explore more?",
        "awesome": "Thanks! There's plenty more to discover. What's next?",
        "great": "Happy to help! What else would you like to know?",
    }
    
    # Conversational patterns that need LLM-generated natural responses
    # These are social/personal questions that deserve human-like answers
    CONVERSATIONAL_LLM_PATTERNS = {
        "how are you", "how are you doing", "how's it going", "how do you do",
        "what's up", "whats up", "sup", "wassup",
        "how are things", "how's everything", "how is everything",
        "are you okay", "are you alright", "you okay", "you alright",
        "good morning", "good afternoon", "good evening", "good night",
        "nice to meet you", "pleased to meet you",
        "what's your name", "who made you", "who created you",
        "are you real", "are you human", "are you a bot", "are you ai",
        "do you have feelings", "can you think", "are you conscious",
    }
    
    # User memory/personal questions - questions about what user told us
    # These need to check conversation history and respond intelligently
    USER_MEMORY_PATTERNS = {
        "what is my name", "what's my name", "whats my name",
        "do you remember my name", "do you know my name",
        "what did i tell you", "what did i say",
        "do you remember", "do you remember me",
        "what do you know about me", "what have i told you",
        "who am i", "my name",
    }

    # NON_QUERY responses - natural silence acknowledgments (not instructional)
    # Organized by context for smarter selection
    NON_QUERY_RESPONSES_FIRST = [
        "🙂",
        "👍",
        "Okay.",
        "Got it.",
    ]
    
    NON_QUERY_RESPONSES_REPEAT = [
        "Mm-hmm.",
        "👍",
        "🙂",
    ]
    
    NON_QUERY_RESPONSES_AFTER_EXPLANATION = [
        "Glad it helped!",
        "Happy to help.",
        "🙂",
    ]
    
    # None = silence (valid conversational response)
    NON_QUERY_RESPONSES_SPAM = [
        None,  # Silence
        None,  # Silence
        "🙂",
    ]

    # AMBIGUOUS_REFERENCE response - when user says "this/that" with no referent
    AMBIGUOUS_REFERENCE_RESPONSE = """I'm not sure what you're referring to. Could you clarify what *this* means?

For example, you can say:
• "Explain point #2"
• "What is the concept you mentioned earlier?"
• "Tell me more about creativity"
• Ask about a specific topic like "What is meditation?" """

    # KG_META_EXPLAIN response - explaining the knowledge graph structure
    KG_META_EXPLAIN_RESPONSE = """In this system:

• **Concepts** are the key ideas or entities discussed in podcasts (e.g., creativity, mindfulness, Phil Jackson).
• **Relationships** describe how those concepts connect (e.g., 'improves', 'leads to', 'influences').

Together, they form a **knowledge graph** that lets the system reason across episodes and find connections between ideas.

You can ask me things like:
• "What concepts are related to creativity?"
• "How does meditation relate to focus?"
• "What practices improve decision-making?"
• "List all concepts" (to explore the knowledge graph)"""

    # Patterns for NON_QUERY detection (not questions, just reactions)
    NON_QUERY_PATTERNS = {
        "ok", "okay", "k", "kk", "hmm", "hm", "huh", "mhm", "uh huh",
        "ah", "oh", "ooh", "aah", "aha", "i see", "alright", "all right",
        "sure", "yep", "yup", "yeah", "yes", "no", "nope", "nah",
        "lol", "haha", "hehe", "lmao", "rofl",
        "are you mad", "are you angry", "are you upset", "are you ok",
        "are you there", "you there", "hello?", "hi?",
        "whatever", "nevermind", "never mind", "nvm", "forget it",
        "idk", "i don't know", "dunno",
    }

    # Deictic patterns - queries with "this/that/it/he/she" that need a referent
    DEICTIC_PATTERNS = {
        "what is this", "what is that", "what is it",
        "what's this", "what's that", "what's it",
        "explain this", "explain that", "explain it",
        "tell me about this", "tell me about that", "tell me about it",
        "can you explain this", "can you explain that",
        "what does this mean", "what does that mean",
        "this", "that", "it",
    }

    # Pronoun patterns - need entity resolution
    PRONOUN_PATTERNS = {
        "what did he say", "what did she say", "what did they say",
        "what he told", "what she told", "what they told",
        "tell me about him", "tell me about her", "tell me about them",
        "who is he", "who is she", "who are they",
        "what does he think", "what does she think",
        "his ideas", "her ideas", "their ideas",
        "his philosophy", "her philosophy", "their philosophy",
    }

    # KG Meta EXPLAIN patterns - questions about the system's knowledge structure
    KG_META_EXPLAIN_PATTERNS = {
        "what are concepts", "what are relationships",
        "what is a concept", "what is a relationship",
        "how does the knowledge graph work",
        "what is the knowledge graph", "what's in the knowledge graph",
        "what entities do you have", "what data do you have",
        "concepts and relationships", "relationships and concepts",
    }

    # KG Meta EXPLORE patterns - requests to list/explore KG contents (needs Neo4j)
    KG_META_EXPLORE_PATTERNS = {
        "list concepts", "list all concepts", "show concepts", "show all concepts",
        "list relationships", "list all relationships", "show relationships",
        "what concepts do you have", "what concepts are there",
        "what relationships do you have", "what relationships are there",
        "show me the concepts", "show me the relationships",
        "explore the knowledge graph", "browse concepts",
        "list entities", "list all entities", "show entities",
    }

    def __init__(
        self,
        model: str = "gpt-5.2",
        workspace_id: Optional[str] = None,
    ):
        """
        Initialize intent classifier.

        Args:
            model: OpenAI model to use
            workspace_id: Workspace identifier
        """
        self.model = model
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger(
            "core_engine.reasoning.intent_classifier",
            workspace_id=self.workspace_id,
        )

        # Initialize OpenAI
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found")
            self.openai_client = OpenAI(api_key=api_key)
            self.logger.info("intent_classifier_initialized", extra={"model": model})
        except Exception as e:
            self.logger.error("intent_classifier_init_failed", extra={"error": str(e)})
            self.openai_client = None

    def classify(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[QueryIntent, Dict[str, Any]]:
        """
        Classify the intent of a user query using a LAYERED approach.
        
        ARCHITECTURE (Industry-Grade):
        ┌─────────────────────────────────────────────────────────────┐
        │ LAYER 1: Hard Rules (Fast Path)                             │
        │ - Catches obvious cases instantly                           │
        │ - GREETING, NON_QUERY, SYSTEM_INFO, etc.                   │
        │ - Zero latency, deterministic                               │
        └─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (if no match)
        ┌─────────────────────────────────────────────────────────────┐
        │ LAYER 2: Semantic Intent Inference (LLM Safety Net)         │
        │ - Handles novel phrasing, paraphrases, creative inputs     │
        │ - "I don't recognize the phrasing, but I recognize intent" │
        │ - Open-world coverage                                       │
        └─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (if LLM unavailable)
        ┌─────────────────────────────────────────────────────────────┐
        │ LAYER 3: Pattern Fallback (Last Resort)                     │
        │ - Broader pattern matching                                  │
        │ - Lower confidence                                          │
        │ - Graceful degradation                                      │
        └─────────────────────────────────────────────────────────────┘

        Args:
            query: User's query text
            conversation_history: Previous conversation messages
            session_metadata: Session metadata including active_entity for reference resolution

        Returns:
            Tuple of (QueryIntent, metadata dict with details)
        """
        query_clean = query.strip()
        query_lower = query_clean.lower()

        # =====================================================
        # LAYER 1: HARD RULES (Fast Path)
        # Catches obvious cases with zero latency
        # =====================================================
        quick_result = self._quick_classify(query_lower, conversation_history, session_metadata)
        if quick_result:
            return quick_result

        # =====================================================
        # LAYER 2: SEMANTIC INTENT INFERENCE (LLM Safety Net)
        # This is the KEY layer that handles open-world inputs
        # "I don't recognize the phrasing, but I recognize the intent"
        # =====================================================
        if self.openai_client:
            return self._llm_classify(query_clean, conversation_history, session_metadata)
        
        # =====================================================
        # LAYER 3: PATTERN FALLBACK (Graceful Degradation)
        # Only used when LLM is unavailable
        # =====================================================
        return self._pattern_classify(query_lower, conversation_history, session_metadata)

    def _quick_classify(
        self,
        query_lower: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[QueryIntent, Dict[str, Any]]]:
        """
        SIMPLIFIED Fast Path - Only handles truly obvious cases.
        
        PRINCIPLE: Let LLM handle 90% of cases. Only intercept when:
        1. It's clearly a non-query (ok, hmm, sure)
        2. It's clearly a greeting (hi, hello)
        3. It's clearly a thank you / acknowledgment
        
        Everything else → LLM classification for intelligent handling.
        
        Returns None if LLM classification is needed.
        """
        import random
        
        # Check for empty or very short queries
        if len(query_lower) < 2:
            return (QueryIntent.CLARIFICATION, {
                "response": "I didn't catch that. Could you please rephrase your question?",
                "confidence": 1.0,
                "requires_search": False,
            })

        query_stripped = query_lower.rstrip("!?.,")

        # ========================================
        # GATE 1: NON_QUERY - Reactions/fillers (ok, hmm, sure)
        # These should NEVER trigger LLM or search
        # ========================================
        if self._is_non_query(query_lower, query_stripped):
            return (QueryIntent.NON_QUERY, {
                "confidence": 1.0,
                "requires_search": False,
            })

        # ========================================
        # GATE 2: GREETING - Simple greetings (hi, hello)
        # Fast path to avoid LLM call for obvious greetings
        # ========================================
        pure_greetings = {
            "hi", "hello", "hey", "hii", "hiii",
            "hi there", "hello there", "hey there",
            "good morning", "good afternoon", "good evening",
            "howdy", "greetings", "yo", "hiya", "heya",
        }
        
        if query_stripped in pure_greetings:
            return (QueryIntent.GREETING, {
                "response": random.choice(self.GREETING_RESPONSES),
                "confidence": 1.0,
                "requires_search": False,
            })

        # ========================================
        # GATE 3: SIMPLE ACKNOWLEDGMENTS (thanks, thank you)
        # Fast path for gratitude expressions
        # ========================================
        simple_thanks = {"thanks", "thank you", "thx", "ty"}
        if query_stripped in simple_thanks:
            return (QueryIntent.CONVERSATIONAL, {
                "confidence": 1.0,
                "requires_search": False,
                "needs_llm_response": True,
                "original_query": query_lower,
                "conversation_type": "acknowledgment",
            })

        # ========================================
        # EVERYTHING ELSE → LLM CLASSIFICATION
        # Let the LLM handle: social questions, knowledge queries,
        # system info, follow-ups, ambiguous references, etc.
        # ========================================
        return None  # Proceed to LLM classification

    def _is_non_query(self, query_lower: str, query_stripped: str) -> bool:
        """
        Determine if the input is a NON_QUERY (acknowledgment/reaction, not a question).
        
        Handles variations like:
        - "ok" / "okay" / "okkk" / "ok ok"
        - "hmm" / "hmm wow" / "hmmm"
        - "ok ok you are correct"
        - "yeah yeah"
        - "haha nice"
        
        Key insight: If the message is PRIMARILY composed of reaction words,
        it's a NON_QUERY, even if it has extra words.
        """
        # Exact matches first (fastest)
        if query_stripped in self.NON_QUERY_PATTERNS:
            return True
        if query_lower in self.NON_QUERY_PATTERNS:
            return True
        
        # Handle repeated patterns like "ok ok", "yeah yeah", "hmm hmm"
        words = query_lower.split()
        if len(words) >= 1:
            # Check if first word is a reaction word
            first_word = words[0].rstrip("!?.,")
            
            # Core reaction words that indicate NON_QUERY
            reaction_words = {
                "ok", "okay", "okkk", "okk", "okok",
                "hmm", "hmmm", "hmmmm", "hm",
                "yeah", "yep", "yup", "yes", "ya",
                "no", "nope", "nah",
                "ah", "oh", "ooh", "aah", "aha",
                "haha", "hehe", "lol", "lmao",
                "sure", "alright", "right",
                "wow", "nice", "cool", "great",
                "correct", "exactly", "true",
            }
            
            if first_word in reaction_words:
                # If it starts with a reaction word, check if the rest is also reactions/filler
                # "ok ok you are correct" → all words are reactions or common fillers
                filler_words = {"you", "are", "is", "that", "this", "it", "i", "a", "the", "so", "very", "really"}
                all_reaction_or_filler = all(
                    w.rstrip("!?.,") in reaction_words or w in filler_words
                    for w in words
                )
                if all_reaction_or_filler:
                    return True
                
                # Even if not all filler, if it's short and starts with reaction, likely NON_QUERY
                if len(words) <= 4 and first_word in {"ok", "okay", "hmm", "yeah", "yes", "no", "haha", "wow"}:
                    # Check if it contains a question word
                    question_words = {"what", "who", "where", "when", "why", "how", "which", "can", "could", "would", "should", "is", "are", "do", "does", "did"}
                    has_question = any(w in question_words for w in words[1:])
                    if not has_question:
                        return True
        
        # Handle elongated patterns like "okkk", "hmmm", "yeahhh"
        import re
        if re.match(r'^(ok+|hmm+|yeah+|yep+|ah+|oh+|haha+|lol+|wow+)$', query_stripped):
            return True
        
        return False

    def _has_clear_referent(
        self,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if conversation history has a clear referent for deictic terms.
        
        A "clear referent" means:
        1. There's an active_entity in session metadata (highest priority)
        2. The assistant previously mentioned numbered lists (1., 2., 3.)
        3. The assistant mentioned named concepts or entities
        4. Substantial content was provided
        
        This is a SIMPLE check - not NLP magic. It catches 90% of cases.
        """
        # HIGHEST PRIORITY: Check for active entity in session metadata
        if session_metadata and session_metadata.get("active_entity"):
            return True
        
        if not conversation_history:
            return False

        # Look at the last 5 messages for context
        recent_messages = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history

        for msg in reversed(recent_messages):
            if msg.get("role") != "assistant":
                continue

            content = msg.get("content", "").lower()

            # Check for numbered lists (strong indicator of referent)
            if any(marker in content for marker in ["1.", "2.", "3.", "1)", "2)", "3)"]):
                return True

            # Check for concept/entity mentions
            entity_markers = [
                "concept", "practice", "idea", "principle", "method",
                "technique", "approach", "strategy", "framework",
                "person", "author", "speaker", "coach", "philosopher",
            ]
            if any(marker in content for marker in entity_markers):
                return True

            # Check for substantial content (more than just a greeting)
            if len(content) > 200:
                return True

        return False

    def _llm_classify(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[QueryIntent, Dict[str, Any]]:
        """
        LAYER 2: Semantic Intent Inference (LLM Safety Net)
        
        This is the KEY layer that handles open-world inputs.
        It answers: "I don't recognize the phrasing, but I recognize the intent."
        
        The LLM:
        - Does NOT generate responses
        - Does NOT explain
        - ONLY classifies into existing intents
        - Handles novel phrasing, paraphrases, creative inputs
        """
        # Get active entity for context
        active_entity = session_metadata.get("active_entity") if session_metadata else None
        system_in_focus = session_metadata.get("system_in_focus", False) if session_metadata else False
        
        # Build conversation context (more context for better understanding)
        context_text = ""
        if conversation_history:
            recent = conversation_history[-7:]  # More context for semantic understanding
            context_text = "\n".join([
                f"{msg.get('role', 'user').title()}: {msg.get('content', '')[:250]}"
                for msg in recent
            ])

        # Check if this is a new conversation
        is_new_conversation = not conversation_history or len(conversation_history) <= 1
        
        # Build rich context
        context_flags = []
        if active_entity:
            context_flags.append(f"ACTIVE ENTITY: \"{active_entity}\" (pronouns like 'he/she/it/this' refer to this)")
        if system_in_focus:
            context_flags.append("SYSTEM IN FOCUS: User was just discussing the system itself")
        
        context_info = "\n- ".join(context_flags) if context_flags else "No special context"
        
        prompt = f"""You are an INTELLIGENT intent classifier for a Podcast Intelligence System.

YOUR ROLE:
- Understand what the user WANTS, not just what they SAID
- Handle novel phrasing, paraphrases, slang, typos, creative inputs
- "I don't recognize the phrasing, but I recognize the intent"
- Be GENEROUS in interpretation - assume good faith

SYSTEM CONTEXT:
- This is {"a NEW conversation" if is_new_conversation else "an ONGOING conversation"}
- {context_info}
- The system has knowledge about podcasts on: philosophy, creativity, coaching, personal development

INTENT CATEGORIES:

1. **GREETING** - Any form of hello/hi/hey, even creative ones
   Examples: "Hi", "Hello there", "Yo", "Howdy", "What's good"

2. **CONVERSATIONAL** - Social interaction, acknowledgments, personal questions, chit-chat
   Examples: "Thanks", "How are you?", "What's your name?", "You're smart", "I'm bored"
   Also: "My name is X", "Nice to meet you", "What's my name?", "Do you remember me?"
   
3. **NON_QUERY** - Reactions, fillers, not seeking information
   Examples: "ok", "hmm", "sure", "yep", "haha", "whatever", "nevermind"
   
4. **SYSTEM_INFO** - Questions about THIS system/assistant (ONLY when NO active entity)
   Examples: "What can you do?", "How does this work?", "What is this system?"
   **NOTE:** If there's an ACTIVE ENTITY, "What is this?" is FOLLOW_UP, not SYSTEM_INFO!
   
5. **KNOWLEDGE_QUERY** - Seeking information about topics IN the podcasts
   Examples: "What is meditation?", "Tell me about creativity", "Who is Phil Jackson?"
   Also: "What practices help with anxiety?", "How do successful people think?"
   
6. **RELATIONSHIP_QUERY** - How concepts connect
   Examples: "How does X relate to Y?", "What connects meditation and focus?"
   
7. **FOLLOW_UP** - Continuing previous topic, referencing earlier content
   Examples: "Tell me more", "What about point 3?", "Explain that further"
   **CRITICAL:** If ACTIVE ENTITY exists, these are ALL FOLLOW_UP:
   - "What is this?" → asking about the active entity's topic
   - "What did he say?" → asking about the active entity
   - "Explain that" → asking about what was just discussed
   - "His philosophy?" → asking about the active entity
   
8. **OUT_OF_SCOPE** - Questions clearly outside podcast knowledge domain
   Examples: "What's the weather?", "Who won the game?", "Write me code"
   
9. **AMBIGUOUS_REFERENCE** - Unclear reference with NO context to resolve
   Examples: "What is this?" (when nothing was discussed)
   NOTE: If there's context or active entity, it's probably FOLLOW_UP instead
   
10. **KG_META_EXPLAIN** - Asking about HOW the system organizes knowledge
    Examples: "What are concepts?", "How does the knowledge graph work?"
    
11. **KG_META_EXPLORE** - Wanting to LIST/BROWSE the knowledge
    Examples: "List all concepts", "Show me what you know", "What topics do you have?"

12. **CLARIFICATION** - User is confused or didn't understand
    Examples: "What?", "I don't get it", "Huh?"

{f"CONVERSATION HISTORY:{chr(10)}{context_text}" if context_text else "No conversation history - this is the FIRST message."}

USER INPUT: "{query}"

CLASSIFICATION RULES (PRIORITY ORDER - FOLLOW STRICTLY):
1. **CRITICAL: If ACTIVE ENTITY exists** and user says "this", "that", "it", "he", "she", "what is this", "explain this", "tell me more" → **FOLLOW_UP** (they're asking about the entity, NOT the system!)
2. ONLY if NO active entity AND user explicitly asks about "this system", "this tool", "what can you do" → SYSTEM_INFO
3. Personal statements ("My name is X") → CONVERSATIONAL
4. Memory questions ("What's my name?") → CONVERSATIONAL  
5. Social questions ("How are you?") → CONVERSATIONAL
6. OUT_OF_SCOPE only for clearly unrelated topics (weather, sports, politics)
7. When truly uncertain → CONVERSATIONAL (let LLM handle it naturally)

**IMPORTANT DEICTIC RESOLUTION:**
- "What is this?" after discussing Iñárritu → FOLLOW_UP (about Iñárritu's ideas)
- "What is this?" after discussing meditation → FOLLOW_UP (about meditation)
- "What is this?" with NO prior topic → SYSTEM_INFO or AMBIGUOUS_REFERENCE
- The ACTIVE ENTITY takes precedence over system context!

REQUIRES_SEARCH RULES:
- TRUE: KNOWLEDGE_QUERY, RELATIONSHIP_QUERY, FOLLOW_UP, KG_META_EXPLORE
- FALSE: Everything else (GREETING, CONVERSATIONAL, NON_QUERY, SYSTEM_INFO, etc.)

Respond with JSON:
{{"intent": "INTENT_NAME", "confidence": 0.0-1.0, "reasoning": "brief why", "entities": [], "requires_search": true/false}}

JSON Response:"""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                temperature=0.0,  # Zero for deterministic, consistent classification
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert intent classifier. Respond ONLY with valid JSON, no markdown or explanation."
                    },
                    {"role": "user", "content": prompt}
                ]
            )

            result_text = response.choices[0].message.content.strip()
            
            # Clean up JSON if wrapped in markdown
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            intent_str = result.get("intent", "UNKNOWN").upper()
            
            # Map intent string to enum, with fallback handling
            if intent_str in QueryIntent.__members__:
                intent = QueryIntent[intent_str]
            else:
                # If LLM returned an unrecognized intent, treat as CONVERSATIONAL
                # This is the "safety net" - let the conversational LLM handle it
                self.logger.warning(f"LLM returned unrecognized intent: {intent_str}, treating as CONVERSATIONAL")
                intent = QueryIntent.CONVERSATIONAL
            
            # CRITICAL: If intent is UNKNOWN, convert to CONVERSATIONAL
            # UNKNOWN should never reach the user - it means classification failed
            if intent == QueryIntent.UNKNOWN:
                intent = QueryIntent.CONVERSATIONAL
                self.logger.info("Converting UNKNOWN intent to CONVERSATIONAL for graceful handling")
            
            metadata = {
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", ""),
                "entities": result.get("entities", []),
                "requires_search": result.get("requires_search", False),  # Default to False for safety
                "original_query": query,  # Store original query for response generation
            }

            # NOTE: Responses are NOT set here - they are determined by get_direct_response()
            # This ensures single source of truth for all response generation
            # The classifier only determines INTENT, the response layer determines OUTPUT
            
            # For CONVERSATIONAL intent, mark for LLM response generation
            if intent == QueryIntent.CONVERSATIONAL:
                metadata["needs_llm_response"] = True
                metadata["conversation_type"] = "llm_classified"
            
            # Add resolved entity if we have an active entity and this is a follow-up
            if intent == QueryIntent.FOLLOW_UP and active_entity:
                metadata["resolved_entity"] = active_entity

            # NOTE: Logging is done in KGReasoner.query(), not here
            # Classifier decides, Reasoner observes

            return (intent, metadata)

        except json.JSONDecodeError as e:
            self.logger.warning("intent_json_parse_failed", extra={"error": str(e)})
            return self._pattern_classify(query.lower(), conversation_history, session_metadata)
        except Exception as e:
            self.logger.error("intent_llm_classify_failed", extra={"error": str(e)})
            return self._pattern_classify(query.lower(), conversation_history, session_metadata)

    def _pattern_classify(
        self,
        query_lower: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[QueryIntent, Dict[str, Any]]:
        """
        Fallback pattern-based classification when LLM is unavailable.
        
        Uses the same gate order as _quick_classify for consistency.
        """
        import random
        query_stripped = query_lower.rstrip("!?.,")
        active_entity = session_metadata.get("active_entity") if session_metadata else None
        
        # GATE 1: NON_QUERY
        if query_stripped in self.NON_QUERY_PATTERNS:
            return (QueryIntent.NON_QUERY, {
                "response": random.choice(self.NON_QUERY_RESPONSES),
                "confidence": 0.9,
                "requires_search": False,
            })

        # GATE 2: Greeting patterns
        greeting_patterns = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if any(query_lower.startswith(p) for p in greeting_patterns):
            return (QueryIntent.GREETING, {
                "response": random.choice(self.GREETING_RESPONSES),
                "confidence": 0.8,
                "requires_search": False,
            })

        # GATE 3: Conversational patterns (without ok/okay which are now NON_QUERY)
        # ALL conversational responses use LLM for intelligent, natural responses
        conv_patterns = ["thanks", "thank you", "cool", "nice", "great", "awesome", "interesting"]
        if any(query_lower.startswith(p) or query_stripped == p for p in conv_patterns):
            return (QueryIntent.CONVERSATIONAL, {
                "confidence": 0.8,
                "requires_search": False,
                "needs_llm_response": True,
                "original_query": query_lower,
                "conversation_type": "acknowledgment",
            })
        
        # GATE 3b: Social/personal questions - use LLM
        for pattern in self.CONVERSATIONAL_LLM_PATTERNS:
            if pattern in query_lower:
                return (QueryIntent.CONVERSATIONAL, {
                    "confidence": 0.85,
                    "requires_search": False,
                    "needs_llm_response": True,
                    "original_query": query_lower,
                    "conversation_type": "social",
                })

        # GATE 4: KG_META_EXPLORE patterns (needs Neo4j)
        for pattern in self.KG_META_EXPLORE_PATTERNS:
            if pattern in query_lower:
                return (QueryIntent.KG_META_EXPLORE, {
                    "confidence": 0.85,
                    "requires_search": True,
                })

        # GATE 5: KG_META_EXPLAIN patterns (no search)
        for pattern in self.KG_META_EXPLAIN_PATTERNS:
            if pattern in query_lower:
                return (QueryIntent.KG_META_EXPLAIN, {
                    "response": self.KG_META_EXPLAIN_RESPONSE,
                    "confidence": 0.85,
                    "requires_search": False,
                })

        # GATE 6: PRONOUN patterns - check for active entity
        for pattern in self.PRONOUN_PATTERNS:
            if pattern in query_lower:
                if active_entity:
                    return (QueryIntent.FOLLOW_UP, {
                        "confidence": 0.85,
                        "requires_search": True,
                        "resolved_entity": active_entity,
                    })
                else:
                    return (QueryIntent.AMBIGUOUS_REFERENCE, {
                        "response": "I'm not sure who you're referring to. Could you specify the person's name?",
                        "confidence": 0.9,
                        "requires_search": False,
                    })

        # GATE 7: System info patterns (BEFORE deictic to catch "what is this system")
        system_patterns = ["what can you", "who are you", "what are you", "help", "how does this", "this system", "this tool", "this assistant", "this ai"]
        if any(p in query_lower for p in system_patterns):
            return (QueryIntent.SYSTEM_INFO, {
                "confidence": 0.8,
                "requires_search": False,
            })

        # GATE 8: DEICTIC / AMBIGUOUS patterns
        for pattern in self.DEICTIC_PATTERNS:
            if query_stripped == pattern:
                if active_entity:
                    return (QueryIntent.FOLLOW_UP, {
                        "confidence": 0.85,
                        "requires_search": True,
                        "resolved_entity": active_entity,
                    })
                elif not self._has_clear_referent(conversation_history, session_metadata):
                    return (QueryIntent.AMBIGUOUS_REFERENCE, {
                        "response": self.AMBIGUOUS_REFERENCE_RESPONSE,
                        "confidence": 0.9,
                        "requires_search": False,
                    })

        # Follow-up patterns (only if there's a referent)
        followup_patterns = ["tell me more", "more about", "expand on", "what about", "the first", "the second", "point #", "item #"]
        if any(p in query_lower for p in followup_patterns):
            if active_entity:
                return (QueryIntent.FOLLOW_UP, {
                    "requires_search": True,
                    "confidence": 0.8,
                    "resolved_entity": active_entity,
                })
            elif self._has_clear_referent(conversation_history, session_metadata):
                return (QueryIntent.FOLLOW_UP, {
                    "requires_search": True,
                    "confidence": 0.7,
                })
            else:
                return (QueryIntent.AMBIGUOUS_REFERENCE, {
                    "response": self.AMBIGUOUS_REFERENCE_RESPONSE,
                    "confidence": 0.8,
                    "requires_search": False,
                })

        # Relationship patterns
        relationship_patterns = ["relate to", "relates to", "relationship between", "connection between", "connected to"]
        if any(p in query_lower for p in relationship_patterns):
            return (QueryIntent.RELATIONSHIP_QUERY, {
                "requires_search": True,
                "confidence": 0.8,
            })

        # Out of scope patterns
        out_of_scope_patterns = ["weather", "president", "prime minister", "stock", "sports", "score", "news today"]
        if any(p in query_lower for p in out_of_scope_patterns):
            return (QueryIntent.OUT_OF_SCOPE, {
                "response": "I'm sorry, but that question is outside my knowledge domain. I specialize in insights from podcasts about philosophy, creativity, coaching, and personal development.",
                "confidence": 0.7,
                "requires_search": False,
            })

        # Default to knowledge query (but with lower confidence)
        return (QueryIntent.KNOWLEDGE_QUERY, {
            "requires_search": True,
            "confidence": 0.5,
        })

    def _get_conversational_response(self, query_lower: str) -> str:
        """Get appropriate conversational response."""
        for key, response in self.CONVERSATIONAL_RESPONSES.items():
            if key in query_lower:
                return response
        return "Let me know if you have any other questions!"

    def _is_light_system_question(self, question: str) -> bool:
        """
        Determine if a SYSTEM_INFO question is "light" (casual) vs "deep" (detailed).
        
        Light questions get short, conversational responses.
        Deep questions get the full system intro.
        
        Examples:
        - Light: "what you do?", "who are you?", "what is this?"
        - Deep: "how does this system work internally?", "explain your architecture"
        """
        if not question:
            return True  # Default to light if no question provided
        
        question_lower = question.lower().strip().rstrip("?!.")
        
        # Explicit light patterns - casual, short questions
        light_patterns = {
            "what you do", "what do you do",
            "who are you", "what are you",
            "what is this", "what's this",
            "what is this ai", "what is this bot",
            "help", "help me",
        }
        
        if question_lower in light_patterns:
            return True
        
        # Short questions (4 words or less) are usually light
        if len(question_lower.split()) <= 4:
            return True
        
        # Deep patterns - detailed questions
        deep_patterns = [
            "how does", "explain", "describe", "tell me about",
            "what can you", "what are your capabilities",
            "architecture", "internally", "in detail",
        ]
        
        if any(pattern in question_lower for pattern in deep_patterns):
            return False
        
        # Default to light for ambiguous cases
        return True

    def _get_non_query_response(
        self,
        session_metadata: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """
        Get contextual NON_QUERY response based on conversation state.
        
        Returns None for silence (valid conversational response).
        
        Strategy:
        - First NON_QUERY: emoji or "okay"
        - Repeated NON_QUERY: shorter response or silence
        - After long explanation: "Glad it helped"
        - Spam (3+): silence
        """
        import random
        
        # Get NON_QUERY count from session
        non_query_count = 0
        if session_metadata:
            non_query_count = session_metadata.get("non_query_count", 0)
        
        # Check if last assistant message was a long explanation
        last_was_explanation = False
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if len(content) > 300:  # Long explanation
                        last_was_explanation = True
                    break
        
        # Select response based on context
        if non_query_count >= 3:
            # Spam - mostly silence
            return random.choice(self.NON_QUERY_RESPONSES_SPAM)
        elif last_was_explanation:
            # After explanation - acknowledge helpfulness
            return random.choice(self.NON_QUERY_RESPONSES_AFTER_EXPLANATION)
        elif non_query_count >= 1:
            # Repeat - shorter response
            return random.choice(self.NON_QUERY_RESPONSES_REPEAT)
        else:
            # First time - normal acknowledgment
            return random.choice(self.NON_QUERY_RESPONSES_FIRST)

    def _generate_conversational_llm_response(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        conversation_type: Optional[str] = None,
    ) -> str:
        """
        Generate a natural, human-like response for ANY conversational query using LLM.
        
        This is the INTELLIGENT response generator that handles:
        - Social questions: "How are you?", "What's your name?"
        - Acknowledgments: "Thanks", "Interesting", "Cool"
        - Personal questions: "Are you a bot?", "Do you have feelings?"
        - User memory questions: "What is my name?", "Do you remember me?"
        - ANY other conversational input that doesn't need knowledge search
        
        The LLM understands context and generates appropriate, natural responses.
        """
        if not self.openai_client:
            # Fallback if no LLM available
            return "I'm here to help! 😊 What would you like to explore from the podcasts?"
        
        try:
            # Build conversation context for the LLM - MORE context for memory questions
            context_text = ""
            context_limit = 10 if conversation_type == "user_memory" else 5
            if conversation_history:
                recent = conversation_history[-context_limit:]
                context_text = "\n".join([
                    f"{msg.get('role', 'user').title()}: {msg.get('content', '')[:200]}"
                    for msg in recent
                ])
            
            # Special handling based on conversation type
            special_instructions = ""
            if conversation_type == "user_memory":
                special_instructions = """
IMPORTANT - USER MEMORY QUESTION:
The user is asking about something they told you earlier in this conversation.
- CAREFULLY search the conversation history for any personal information the user shared
- Look for: their name, preferences, things they mentioned about themselves
- If you find the information, respond naturally with it
- If you DON'T find it in the history, honestly say you don't have that information
- Example: If user said "My name is John" earlier and now asks "What is my name?", respond "Your name is John! 😊"
- Example: If they never told you their name, say "I don't think you've told me your name yet. What should I call you?"
"""
            elif conversation_type == "unknown_fallback":
                special_instructions = """
IMPORTANT - OPEN-ENDED INPUT:
The user's input didn't match any specific category. Respond naturally and helpfully.
- If it seems like a greeting, greet them warmly
- If it seems like a question, try to understand and respond appropriately
- If it's unclear, ask a friendly clarifying question
- Be conversational and helpful, not robotic
- If they seem to want to explore podcast topics, invite them to ask about specific concepts
"""
            
            system_prompt = f"""You are a friendly, intelligent Podcast Intelligence Assistant.
You help users explore insights from podcast transcripts about philosophy, creativity, coaching, and personal development.
{special_instructions}
YOUR PERSONALITY:
- Warm, natural, and genuinely conversational
- Intelligent and thoughtful in responses
- Not robotic or scripted
- Occasionally uses emojis (1-2 max, not every message)
- Adapts tone to match the user's energy
- REMEMBERS what the user tells you in the conversation

RESPONSE GUIDELINES:
- Keep responses brief but meaningful (1-3 sentences)
- Be genuine - don't give generic responses
- If user says "thanks" or "interesting", acknowledge naturally and invite further exploration
- If user asks personal questions, answer warmly and redirect gently
- If user seems frustrated or confused, be empathetic
- Match the user's formality level
- NEVER be preachy or over-explain your purpose
- If user asks about something they told you, CHECK THE CONVERSATION HISTORY

{"CONVERSATION HISTORY:" + chr(10) + context_text if context_text else "This is the START of the conversation."}

EXAMPLES OF GOOD RESPONSES:
- User: "How are you?" → "Doing great! 😊 What's on your mind today?"
- User: "Thanks" → "You're welcome! Anything else you'd like to explore?"
- User: "Interesting" → "Right? There's so much more to dig into. What caught your attention?"
- User: "Are you real?" → "I'm an AI, but I'm here and ready to help! What would you like to know?"
- User: "Good morning" → "Morning! ☀️ Ready to explore some ideas?"
- User: "What is my name?" (if they said "I'm Sarah" earlier) → "Your name is Sarah! 😊"
- User: "What is my name?" (if they never said) → "I don't think you've told me your name yet. What should I call you?"
- User: "You're smart" → "Thanks! I try my best. What can I help you with?"
- User: "I'm bored" → "Let's fix that! Want to explore some fascinating ideas from the podcasts?"
- User: "Tell me a joke" → "I'm better at insights than jokes 😄 But I can share some fascinating ideas about creativity or philosophy!"
- User: "What's the meaning of life?" → "Big question! The podcasts have some interesting perspectives on purpose and fulfillment. Want to explore?"

RESPOND NATURALLY TO: "{query}"
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,  # Zero for deterministic classification (was 0.8)
                max_tokens=150,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.warning(f"LLM conversational response failed: {e}")
            # Fallback response
            return "I'm here and ready to help! 😊 What would you like to explore from the podcasts?"

    def get_direct_response(
        self,
        intent: QueryIntent,
        metadata: Dict[str, Any],
        session_metadata: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """
        Get a direct response for intents that don't require search.
        
        SINGLE SOURCE OF TRUTH for all non-search responses.
        Handles:
        - Response generation
        - Repetition throttling (SYSTEM_INFO, etc.)
        - Contextual responses (NON_QUERY)
        
        Returns None if the intent requires RAG/KG search OR for intentional silence.
        """
        import random
        
        # If metadata says search is required, return None
        if metadata.get("requires_search", False):
            return None
        
        # =====================================================
        # NON_QUERY - Contextual response with silence option
        # =====================================================
        if intent == QueryIntent.NON_QUERY:
            return self._get_non_query_response(session_metadata, conversation_history)
        
        # =====================================================
        # GREETING - Random variety
        # =====================================================
        if intent == QueryIntent.GREETING:
            return random.choice(self.GREETING_RESPONSES)
        
        # =====================================================
        # CONVERSATIONAL - ALWAYS use LLM for intelligent responses
        # =====================================================
        if intent == QueryIntent.CONVERSATIONAL:
            # Get the original query from metadata or use a default
            original_query = metadata.get("original_query", "")
            conversation_type = metadata.get("conversation_type", "general")
            
            # ALWAYS use LLM for conversational responses - this is what makes it intelligent
            return self._generate_conversational_llm_response(
                original_query,
                conversation_history,
                conversation_type
            )
        
        # =====================================================
        # SYSTEM_INFO - Tiered response based on question depth
        # Light questions → short answer
        # Deep questions → full intro
        # Repeated → progressively shorter
        # =====================================================
        if intent == QueryIntent.SYSTEM_INFO:
            intro_count = session_metadata.get("intro_count", 0) if session_metadata else 0
            original_question = metadata.get("original_query", "")
            
            # Check if this is a light/casual system question
            is_light = self._is_light_system_question(original_question)
            
            if intro_count == 0:
                if is_light:
                    # Short, conversational response for casual questions
                    return "I help you explore ideas, people, and patterns from podcast transcripts—like creativity, philosophy, coaching, and personal growth. What would you like to know?"
                else:
                    # Full intro for detailed questions like "how does this system work?"
                    return self.SYSTEM_INTRO
            elif intro_count == 1:
                # Second time - medium response
                return "I'm your Podcast Intelligence Assistant! Ask me about concepts, relationships, or ideas from podcasts. What would you like to know?"
            else:
                # Third+ time - redirect
                return "Is there something specific you'd like to know? Try asking about a concept like creativity, meditation, or a person mentioned in the podcasts."
        
        # =====================================================
        # AMBIGUOUS_REFERENCE - Throttled (helpful → shorter)
        # =====================================================
        if intent == QueryIntent.AMBIGUOUS_REFERENCE:
            ambiguous_count = session_metadata.get("ambiguous_count", 0) if session_metadata else 0
            if ambiguous_count <= 1:
                return self.AMBIGUOUS_REFERENCE_RESPONSE
            else:
                return "Could you be more specific? What topic or concept are you asking about?"
        
        # =====================================================
        # OUT_OF_SCOPE - Throttled
        # =====================================================
        if intent == QueryIntent.OUT_OF_SCOPE:
            oos_count = session_metadata.get("out_of_scope_count", 0) if session_metadata else 0
            if oos_count == 0:
                return "I'm sorry, but that question is outside my knowledge domain. I specialize in insights from podcasts about philosophy, creativity, coaching, and personal development. Is there something in those areas I can help you with?"
            else:
                return "That's outside my expertise. I focus on philosophy, creativity, coaching, and personal development topics."
        
        # =====================================================
        # Other intents - Standard responses
        # =====================================================
        standard_responses = {
            QueryIntent.KG_META_EXPLAIN: self.KG_META_EXPLAIN_RESPONSE,
            QueryIntent.CLARIFICATION: "I'm not sure I understood that. Could you please rephrase your question?",
        }
        
        return standard_responses.get(intent)

    def should_search(self, intent: QueryIntent, metadata: Dict[str, Any]) -> bool:
        """
        Determine if the query requires RAG/KG search.
        
        CRITICAL: This is the GATE that prevents unnecessary retrieval.
        
        Rule: "When in doubt — clarify, don't search."
        
        Priority order:
        1. HARD BLOCK intents → always False
        2. Explicit requires_search=False from LLM → False
        3. Explicit requires_search=True from LLM → True (if confident)
        4. Search intents with confidence → True
        5. Default → False (safe fallback)
        """
        # ========================================
        # HARD BLOCK - These intents NEVER search (highest priority)
        # ========================================
        no_search_intents = {
            QueryIntent.GREETING,
            QueryIntent.SYSTEM_INFO,
            QueryIntent.CONVERSATIONAL,
            QueryIntent.CLARIFICATION,
            QueryIntent.OUT_OF_SCOPE,
            QueryIntent.NON_QUERY,
            QueryIntent.AMBIGUOUS_REFERENCE,
            QueryIntent.KG_META_EXPLAIN,  # Explain = no search
        }
        
        if intent in no_search_intents:
            return False
        
        # ========================================
        # TRUST LLM's requires_search signal (if explicit)
        # ========================================
        requires_search = metadata.get("requires_search")
        confidence = metadata.get("confidence", 0.5)
        
        # If LLM explicitly said don't search, trust it
        if requires_search is False:
            return False
        
        # If LLM explicitly said search AND confident, trust it
        if requires_search is True and confidence >= 0.6:
            return True
        
        # ========================================
        # FALLBACK - Intent-based decision with confidence gate
        # ========================================
        search_intents = {
            QueryIntent.KNOWLEDGE_QUERY,
            QueryIntent.RELATIONSHIP_QUERY,
            QueryIntent.FOLLOW_UP,
            QueryIntent.KG_META_EXPLORE,  # Explore = needs Neo4j search
        }
        
        # Only search if intent suggests it AND confidence is high enough
        if intent in search_intents and confidence >= 0.6:
            return True
        
        # Default: don't search (safe fallback)
        return False

