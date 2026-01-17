"""
INTELLIGENT QUERY GENERATOR V2
Built from scratch with GPT-4.1 for superior natural language understanding.
Generates accurate Cypher queries for the Knowledge Graph.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
import os
import json
from dotenv import load_dotenv

from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger

load_dotenv()


# Complete schema definition for the LLM
SCHEMA_DEFINITION = """
# KNOWLEDGE GRAPH SCHEMA

## Node Types (Labels):
1. **Concept** - Abstract ideas, theories, frameworks
   - Properties: id, name, type, description, episode_ids[], workspace_id, confidence
   
2. **Practice** - Actions, methods, techniques (e.g., meditation, walking)
   - Properties: id, name, description, episode_ids[], workspace_id
   
3. **CognitiveState** - Mental states, emotions (e.g., mindfulness, awareness)
   - Properties: id, name, description, episode_ids[], workspace_id
   
4. **BehavioralPattern** - Recurring behaviors, habits
   - Properties: id, name, description, episode_ids[], workspace_id
   
5. **Principle** - Guiding principles, frameworks
   - Properties: id, name, description, episode_ids[], workspace_id
   
6. **Outcome** - Results, effects, consequences
   - Properties: id, name, description, episode_ids[], workspace_id
   
7. **Causality** - Cause-effect relationships as concepts
   - Properties: id, name, description, episode_ids[], workspace_id
   
8. **Person** - Named individuals (speakers, guests)
   - Properties: id, name, episode_ids[], workspace_id
   
9. **Quote** - Important quotes from transcripts
   - Properties: id, text, speaker, timestamp, episode_id, workspace_id
   
10. **Episode** - Podcast episodes
    - Properties: id, title, workspace_id

## Relationship Types:
1. **CAUSES** - Source causes target (direct causation)
2. **INFLUENCES** - Source influences target (indirect effect)
3. **OPTIMIZES** - Source optimizes/improves target
4. **ENABLES** - Source enables/makes possible target
5. **REDUCES** - Source reduces target
6. **LEADS_TO** - Source leads to target
7. **REQUIRES** - Source requires target (dependency)
8. **RELATES_TO** - General meaningful relationship
9. **IS_PART_OF** - Source is part of target
10. **SAID** - Person said a Quote
11. **ABOUT** - Quote is about a Concept
12. **MENTIONED_IN** - Concept mentioned in Episode
13. **CROSS_EPISODE** - Concept appears across episodes

## Important Notes:
- ALL nodes have a `workspace_id` property for multi-tenancy
- Concepts can have multiple labels (e.g., :Concept:Practice)
- episode_ids is an array of episode identifiers
- Use CASE-INSENSITIVE matching with toLower() for names
- Always filter by workspace_id in WHERE clauses
"""


class IntelligentQueryGenerator:
    """
    Intelligent query generator using GPT-4.1 for natural language understanding.
    Generates accurate Cypher queries from natural language questions.
    """

    def __init__(
        self,
        client: Neo4jClient,
        workspace_id: Optional[str] = None,
        model: str = "gpt-4.1",
    ):
        """
        Initialize intelligent query generator.

        Args:
            client: Neo4j client
            workspace_id: Workspace identifier
            model: OpenAI model to use (default: gpt-4.1)
        """
        self.client = client
        self.workspace_id = workspace_id or "default"
        self.model = model
        self.logger = get_logger(
            "core_engine.reasoning.query_generator_v2",
            workspace_id=self.workspace_id,
        )

        # Initialize OpenAI
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.openai_client = OpenAI(api_key=api_key)
            self.logger.info("openai_client_initialized", extra={"model": model})
        except Exception as e:
            self.logger.error("openai_init_failed", extra={"error": str(e)})
            raise

    def generate_cypher(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate Cypher query from natural language question using GPT-4.1.

        Args:
            question: Natural language question
            context: Optional context (conversation history, etc.)

        Returns:
            Cypher query string
        """
        # Expand question with context if available
        expanded_question = self._expand_question_with_context(question, context)
        
        # Generate Cypher using GPT-4.1
        try:
            cypher = self._generate_with_llm(expanded_question, context)
            self.logger.info(
                "cypher_generated",
                extra={
                    "question": question[:100],
                    "cypher": cypher[:200],
                }
            )
            return cypher
        except Exception as e:
            self.logger.error(
                "cypher_generation_failed",
                extra={"question": question[:100], "error": str(e)}
            )
            # Fallback to simple query
            return self._generate_fallback_query(expanded_question)

    def _generate_with_llm(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate Cypher using GPT-4.1 with intelligent understanding.

        Args:
            question: Natural language question (potentially expanded)
            context: Optional context

        Returns:
            Cypher query
        """
        # Build conversation context if available
        conversation_context = ""
        if context and context.get("conversation_history"):
            history = context["conversation_history"][-5:]  # Last 5 messages
            if history:
                conversation_context = "\n\n## Previous Conversation:\n"
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")[:200]
                    conversation_context += f"{role.title()}: {content}\n"

        # Build the prompt for GPT-4.1
        prompt = f"""You are an expert Cypher query generator for a Knowledge Graph about podcast transcripts on philosophy, creativity, coaching, and personal development.

{SCHEMA_DEFINITION}

## Your Task:
Generate a Cypher query to answer the following question. The query MUST:
1. Filter by workspace_id = '{self.workspace_id}' in ALL WHERE clauses
2. Use CASE-INSENSITIVE matching with toLower() for text comparisons
3. Return meaningful results with proper labels
4. Handle relationships correctly
5. Be syntactically correct Neo4j Cypher
6. LIMIT results appropriately (10-20 for concepts, 5-10 for detailed info)

## Question Understanding:
- "What is X?" → Find concept X with its description, relationships, episodes
- "How does X relate to Y?" → Find relationships between X and Y
- "What practices improve/optimize X?" → Find practices that OPTIMIZES X
- "What causes X?" → Find concepts that CAUSES X
- "What concepts appear in multiple episodes?" → Find concepts with len(episode_ids) >= 2
- "What are the core ideas about X?" → Find concepts related to X with high importance
- "Who said X?" → Find quotes containing X and their speakers

## Examples:

### Example 1: "What is creativity?"
```cypher
MATCH (c)
WHERE c.workspace_id = 'default'
  AND toLower(c.name) CONTAINS 'creativity'
OPTIONAL MATCH (c)-[r]->(related)
WHERE related.workspace_id = 'default'
RETURN 
  c.name as name,
  c.type as type,
  c.description as description,
  c.episode_ids as episode_ids,
  collect(DISTINCT {{rel: type(r), target: related.name}})[0..5] as relationships
LIMIT 5
```

### Example 2: "How does meditation relate to creativity?"
```cypher
MATCH (source)
WHERE source.workspace_id = 'default'
  AND toLower(source.name) CONTAINS 'meditation'
MATCH (target)
WHERE target.workspace_id = 'default'
  AND toLower(target.name) CONTAINS 'creativity'
MATCH path = (source)-[r*1..2]-(target)
RETURN 
  source.name as source,
  [rel in relationships(path) | type(rel)] as relationships,
  target.name as target,
  length(path) as path_length
ORDER BY path_length
LIMIT 10
```

### Example 3: "What practices optimize clarity?"
```cypher
MATCH (practice)-[r:OPTIMIZES]->(outcome)
WHERE practice.workspace_id = 'default'
  AND outcome.workspace_id = 'default'
  AND (practice:Practice OR practice:Concept)
  AND toLower(outcome.name) CONTAINS 'clarity'
RETURN 
  practice.name as practice,
  type(r) as relationship,
  outcome.name as outcome,
  r.description as how,
  practice.episode_ids as episodes
ORDER BY size(practice.episode_ids) DESC
LIMIT 10
```

### Example 4: "What concepts appear in multiple episodes?"
```cypher
MATCH (c)
WHERE c.workspace_id = 'default'
  AND c.episode_ids IS NOT NULL
  AND size(c.episode_ids) >= 2
RETURN 
  c.name as concept,
  c.type as type,
  c.episode_ids as episodes,
  size(c.episode_ids) as episode_count
ORDER BY episode_count DESC
LIMIT 15
```

### Example 5: "What are quotes about mindfulness?"
```cypher
MATCH (q:Quote)-[:ABOUT]->(c)
WHERE q.workspace_id = 'default'
  AND c.workspace_id = 'default'
  AND toLower(c.name) CONTAINS 'mindfulness'
RETURN 
  q.text as quote,
  q.speaker as speaker,
  q.timestamp as timestamp,
  c.name as about,
  q.episode_id as episode
LIMIT 10
```
{conversation_context}

## Current Question:
"{question}"

## Instructions:
1. Analyze the question to understand what the user wants
2. Generate a Cypher query that accurately answers the question
3. Return ONLY the Cypher query, no explanations
4. Ensure the query is syntactically correct
5. Always filter by workspace_id = '{self.workspace_id}'
6. Use toLower() for case-insensitive text matching
7. Return meaningful column names
8. LIMIT results appropriately

Generate the Cypher query now:"""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                temperature=0.1,  # Low temperature for precise query generation
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Cypher query generator. You understand natural language questions and generate accurate, syntactically correct Cypher queries for Neo4j. You ALWAYS return ONLY the Cypher query, no explanations or markdown."
                    },
                    {"role": "user", "content": prompt}
                ]
            )

            cypher = response.choices[0].message.content.strip()
            
            # Clean up the response (remove markdown if present)
            cypher = cypher.replace("```cypher", "").replace("```", "").strip()
            
            return cypher

        except Exception as e:
            self.logger.error("llm_cypher_generation_failed", extra={"error": str(e)})
            raise

    def _expand_question_with_context(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Expand question with conversation context to resolve pronouns.
        
        Args:
            question: Original question
            context: Optional context with conversation_history
            
        Returns:
            Expanded question with pronouns resolved
        """
        if not context or not context.get("conversation_history"):
            return question
        
        # Check if question has pronouns or references
        question_lower = question.lower()
        has_pronouns = any(word in question_lower for word in [
            "he", "she", "it", "they", "them", "his", "her", "their",
            "that", "this", "those", "these"
        ])
        
        if not has_pronouns:
            return question
        
        # Use GPT-4.1 to expand the question
        try:
            history = context["conversation_history"][-5:]
            history_text = "\n".join([
                f"{msg.get('role', 'user').title()}: {msg.get('content', '')[:200]}"
                for msg in history
            ])
            
            prompt = f"""Given the conversation history, expand the following question by resolving any pronouns or references.

Conversation History:
{history_text}

Current Question: "{question}"

Return ONLY the expanded question with pronouns resolved. If no pronouns need resolving, return the original question.

Expanded Question:"""

            response = self.openai_client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": "You resolve pronouns and references in questions based on conversation history. Return only the expanded question."
                    },
                    {"role": "user", "content": prompt}
                ]
            )

            expanded = response.choices[0].message.content.strip()
            
            self.logger.info(
                "question_expanded",
                extra={
                    "original": question,
                    "expanded": expanded,
                }
            )
            
            return expanded

        except Exception as e:
            self.logger.warning("question_expansion_failed", extra={"error": str(e)})
            return question

    def _generate_fallback_query(self, question: str) -> str:
        """
        Generate a simple fallback query when LLM fails.
        
        Args:
            question: Natural language question
            
        Returns:
            Simple Cypher query
        """
        # Extract keywords
        import re
        keywords = re.findall(r'\b\w+\b', question.lower())
        keywords = [k for k in keywords if len(k) > 3 and k not in [
            "what", "how", "when", "where", "does", "the", "is", "are"
        ]]
        
        if not keywords:
            # Return a query that gets some concepts
            return f"""
MATCH (c)
WHERE c.workspace_id = '{self.workspace_id}'
RETURN c.name as name, c.type as type, c.description as description
LIMIT 10
"""
        
        # Build a simple search query
        keyword_conditions = " OR ".join([
            f"toLower(c.name) CONTAINS '{k}'" for k in keywords[:3]
        ])
        
        return f"""
MATCH (c)
WHERE c.workspace_id = '{self.workspace_id}'
  AND ({keyword_conditions})
OPTIONAL MATCH (c)-[r]->(related)
WHERE related.workspace_id = '{self.workspace_id}'
RETURN 
  c.name as name,
  c.type as type,
  c.description as description,
  collect(DISTINCT {{rel: type(r), target: related.name}})[0..5] as relationships
LIMIT 10
"""

    def execute_query(self, cypher: str) -> List[Dict[str, Any]]:
        """
        Execute Cypher query and return results.
        
        Args:
            cypher: Cypher query string
            
        Returns:
            List of result dictionaries
        """
        try:
            results = self.client.execute_read(cypher, {"workspace_id": self.workspace_id})
            self.logger.info(
                "query_executed",
                extra={"result_count": len(results)}
            )
            return results
        except Exception as e:
            self.logger.error(
                "query_execution_failed",
                extra={"cypher": cypher[:200], "error": str(e)}
            )
            raise

