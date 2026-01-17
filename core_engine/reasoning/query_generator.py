"""
Natural language to Cypher query generation.
Converts user questions to Cypher queries for Neo4j.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger


class QueryGenerator:
    """Generate Cypher queries from natural language."""

    def __init__(
        self,
        client: Neo4jClient,
        workspace_id: Optional[str] = None,
        use_llm: bool = True,
    ):
        """
        Initialize query generator.

        Args:
            client: Neo4j client
            workspace_id: Workspace identifier
            use_llm: Whether to use LLM for query generation (default: True)
        """
        self.client = client
        self.workspace_id = workspace_id or "default"
        self.use_llm = use_llm
        self.logger = get_logger(
            "core_engine.reasoning.query_generator",
            workspace_id=self.workspace_id,
        )

    def generate_cypher(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate Cypher query from natural language question.

        Args:
            question: Natural language question
            context: Optional context (conversation history, etc.)

        Returns:
            Cypher query string
        """
        # Expand question with conversation context to resolve pronouns
        expanded_question = self._expand_question_with_context(question, context)
        
        if self.use_llm:
            return self._generate_with_llm(expanded_question, context)
        else:
            return self._generate_pattern_based(expanded_question)

    def _generate_with_llm(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate Cypher using LLM.

        Args:
            question: Natural language question
            context: Optional context

        Returns:
            Cypher query
        """
        # For now, use pattern-based. LLM integration can be added later
        # This would use OpenAI to convert NL to Cypher
        return self._generate_pattern_based(question)

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
            self.logger.debug("no_context_for_expansion", extra={
                "context": {"has_context": bool(context), "has_history": bool(context and context.get("conversation_history")) if context else False}
            })
            return question
        
        # Check if question contains pronouns
        pronouns = ["he", "she", "it", "they", "him", "her", "them", "his", "hers", "their", "that", "this", "these", "those"]
        question_lower = question.lower()
        has_pronoun = any(pronoun in question_lower for pronoun in pronouns)
        
        if not has_pronoun:
            self.logger.debug("no_pronouns_in_question", extra={"context": {"question": question}})
            return question
        
        # Get recent conversation history
        history = context.get("conversation_history", [])
        if not history:
            return question
        
        # Use LLM to resolve pronouns more accurately
        try:
            from openai import OpenAI
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Build conversation history text - include more messages to capture numbered lists
            # For assistant messages, include full content (they might have numbered lists)
            history_text = "\n".join([
                f"{'User' if msg.get('role') == 'user' else 'Assistant'}: {msg.get('content', '')}"
                for msg in history[-10:]  # Last 10 messages to capture full context
            ])
            
            # Prompt LLM to resolve pronouns and references (like "Point # 5")
            resolution_prompt = f"""Given this conversation history and the current question, resolve any references in the question:
- Pronouns (he, she, it, they, his, her, etc.)
- Numbered references (Point # 5, Item # 3, etc.)
- Other references (that, this, the first one, etc.)

Conversation History:
{history_text}

Current Question: {question}

Instructions:
1. If the question references a numbered item (e.g., "Point # 5", "Item # 3"), find that item in the previous Assistant messages and expand the question to include what that point/item was about.
2. If the question uses pronouns (he, she, it, they, etc.), identify what they refer to from the conversation history and replace them with the actual name/entity.
3. If the question uses other references (that, this, the first one), identify what they refer to and expand the question.
4. Return ONLY the resolved/expanded question, nothing else.
5. If no references are found or cannot be resolved, return the original question unchanged.

Resolved Question:"""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a pronoun resolution assistant. Resolve pronouns to actual entities based on conversation context."},
                    {"role": "user", "content": resolution_prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            resolved_question = response.choices[0].message.content.strip()
            
            # Remove quotes if LLM added them
            if resolved_question.startswith('"') and resolved_question.endswith('"'):
                resolved_question = resolved_question[1:-1]
            if resolved_question.startswith("'") and resolved_question.endswith("'"):
                resolved_question = resolved_question[1:-1]
            
            if resolved_question != question and len(resolved_question) > 0:
                self.logger.info("pronoun_resolved_with_llm", extra={
                    "context": {
                        "original": question,
                        "resolved": resolved_question,
                        "history_count": len(history)
                    }
                })
                return resolved_question
        except Exception as e:
            self.logger.warning("pronoun_resolution_llm_failed", extra={
                "context": {"error": str(e), "question": question}
            })
            # Fallback to simple pattern matching
            # Find the most recent mention of a person/entity
            recent_entities = []
            import re
            for msg in reversed(history[-5:]):  # Last 5 messages
                content = msg.get("content", "")
                # Extract capitalized words (likely names/entities)
                entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
                recent_entities.extend(entities)
            
            # If we found entities, try to resolve pronouns
            if recent_entities:
                # Use the most recent unique entity
                unique_entities = []
                seen = set()
                for entity in reversed(recent_entities):
                    if entity not in seen and len(entity) > 2:
                        unique_entities.append(entity)
                        seen.add(entity)
                
                if unique_entities:
                    # Replace pronouns with the most recent entity
                    resolved_question = question
                    most_recent_entity = unique_entities[0]
                    
                    # Simple pronoun replacement
                    if " he " in question_lower or question_lower.startswith("he ") or question_lower.endswith(" he"):
                        resolved_question = question.replace(" he ", f" {most_recent_entity} ").replace("He ", f"{most_recent_entity} ").replace(" he", f" {most_recent_entity}")
                    if " his " in question_lower or question_lower.startswith("his "):
                        resolved_question = resolved_question.replace(" his ", f" {most_recent_entity}'s ").replace("His ", f"{most_recent_entity}'s ")
                    if " him " in question_lower or question_lower.startswith("him "):
                        resolved_question = resolved_question.replace(" him ", f" {most_recent_entity} ").replace("Him ", f"{most_recent_entity} ")
                    if " what he " in question_lower:
                        resolved_question = resolved_question.replace(" what he ", f" what {most_recent_entity} ").replace("What he ", f"What {most_recent_entity} ")
                    if " what did he " in question_lower:
                        resolved_question = resolved_question.replace(" what did he ", f" what did {most_recent_entity} ").replace("What did he ", f"What did {most_recent_entity} ")
                    
                    if resolved_question != question:
                        self.logger.info("pronoun_resolved_fallback", extra={
                            "context": {
                                "original": question,
                                "resolved": resolved_question,
                                "entity": most_recent_entity
                            }
                        })
                        return resolved_question
        
        return question
    
    def _generate_pattern_based(self, question: str) -> str:
        """
        Generate Cypher using pattern matching.

        Args:
            question: Natural language question (may be expanded with context)

        Returns:
            Cypher query
        """
        # Store question for parameter extraction
        self._last_question = question
        question_lower = question.lower()
        
        # ===== CLIENT QUESTION PATTERNS =====
        
        # Pattern 1: "How does X relate to Y?" - Relationship query
        if "how does" in question_lower and "relate" in question_lower:
            x, y = self._extract_two_concepts(question)
            # Extract keywords from concepts for flexible matching
            x_keywords = [w for w in x.split() if len(w) > 2]
            y_keywords = [w for w in y.split() if len(w) > 2]
            return f"""
            // Find concepts matching X (flexible matching)
            MATCH (c1)
            WHERE c1.workspace_id = $workspace_id
              AND (
                ANY(keyword IN $x_keywords WHERE toLower(c1.name) CONTAINS keyword)
                OR ANY(keyword IN $x_keywords WHERE toLower(c1.description) CONTAINS keyword)
                OR toLower(c1.name) CONTAINS toLower($concept_x)
              )
            // Find concepts matching Y (flexible matching)
            MATCH (c2)
            WHERE c2.workspace_id = $workspace_id
              AND (
                ANY(keyword IN $y_keywords WHERE toLower(c2.name) CONTAINS keyword)
                OR ANY(keyword IN $y_keywords WHERE toLower(c2.description) CONTAINS keyword)
                OR toLower(c2.name) CONTAINS toLower($concept_y)
              )
            // Find paths between them
            MATCH path = shortestPath((c1)-[r*1..3]-(c2))
            WITH path, relationships(path) as rels, nodes(path) as nodes, c1, c2
            RETURN 
                c1.name as source_concept,
                c1.type as source_type,
                c2.name as target_concept,
                c2.type as target_type,
                [node IN nodes | node.name] as path_nodes,
                [rel IN rels | type(rel)] as relationship_types,
                [rel IN rels | rel.description] as descriptions,
                length(path) as path_length
            ORDER BY path_length ASC
            LIMIT 10
            """
        
        # Pattern 2: "What practices are most associated with improving X?" or "practices...improving/clarity"
        if ("practice" in question_lower and ("improving" in question_lower or "improve" in question_lower or "optimize" in question_lower or "enable" in question_lower or "associated" in question_lower)):
            outcome = self._extract_outcome_from_question(question)
            # Use case-insensitive matching for relationship types (handle both OPTIMIZES and optimizes)
            return f"""
            MATCH (p:Practice)-[r]->(o)
            WHERE p.workspace_id = $workspace_id
              AND o.workspace_id = $workspace_id
              AND (toLower(type(r)) IN ['optimizes', 'enables', 'influences'] 
                   OR type(r) IN ['OPTIMIZES', 'ENABLES', 'INFLUENCES'])
              AND (toLower(o.name) CONTAINS toLower($outcome) OR toLower(o.description) CONTAINS toLower($outcome))
            RETURN 
                p.name as practice,
                p.description as practice_description,
                type(r) as relationship_type,
                r.description as relationship_description,
                o.name as outcome,
                r.episode_ids as episode_ids,
                r.source_paths as source_paths,
                r.timestamps as timestamps
            ORDER BY size(r.episode_ids) DESC
            LIMIT 20
            """
        
        # Pattern 3: "What did Speaker A consistently emphasize about X?" - Speaker-anchored query
        if ("did" in question_lower and "consistently" in question_lower and "emphasize" in question_lower) or \
           ("did" in question_lower and "emphasize" in question_lower):
            speaker, concept = self._extract_speaker_and_concept(question)
            return f"""
            MATCH (person:Person)-[r]->(c)
            WHERE person.workspace_id = $workspace_id
              AND c.workspace_id = $workspace_id
              AND (toLower(person.name) CONTAINS toLower($speaker))
              AND (toLower(c.name) CONTAINS toLower($concept) OR toLower(c.description) CONTAINS toLower($concept))
              AND r.speakers IS NOT NULL
              AND ANY(speaker IN r.speakers WHERE toLower(speaker) CONTAINS toLower($speaker))
            RETURN 
                person.name as speaker,
                c.name as concept,
                type(r) as relationship_type,
                r.description as description,
                r.text_spans as quotes,
                r.episode_ids as episode_ids,
                r.timestamps as timestamps,
                r.source_paths as source_paths
            ORDER BY size(r.episode_ids) DESC
            LIMIT 20
            """
        
        # Pattern 4: "If someone wants to reduce X, what concepts or practices..." - Multi-hop reasoning
        if ("reduce" in question_lower or "overcome" in question_lower) and ("practice" in question_lower or "concept" in question_lower):
            problem = self._extract_problem_from_question(question)
            # Use case-insensitive relationship matching
            return f"""
            MATCH path = (problem)-[r*1..2]-(factor)-[r2]-(solution:Practice)
            WHERE problem.workspace_id = $workspace_id
              AND solution.workspace_id = $workspace_id
              AND (toLower(problem.name) CONTAINS toLower($problem) OR toLower(problem.description) CONTAINS toLower($problem))
              AND ALL(rel IN relationships(path) WHERE 
                  toLower(type(rel)) IN ['reduces', 'causes', 'influences', 'optimizes', 'enables']
                  OR type(rel) IN ['REDUCES', 'CAUSES', 'INFLUENCES', 'OPTIMIZES', 'ENABLES'])
            WITH path, problem, solution, relationships(path) as rels
            RETURN DISTINCT
                problem.name as problem,
                solution.name as practice,
                solution.description as practice_description,
                [rel IN rels | type(rel)] as relationship_path,
                solution.episode_ids as episode_ids,
                solution.source_paths as source_paths
            LIMIT 20
            """
        
        # Pattern 5: "What are the core ideas that recur most frequently about X?" - Cross-episode pattern
        if ("core idea" in question_lower or "recur" in question_lower or "frequently" in question_lower) and "about" in question_lower:
            topic = self._extract_topic_after_about(question)
            return f"""
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND c.episode_ids IS NOT NULL
              AND size(c.episode_ids) >= 2
              AND (toLower(c.name) CONTAINS toLower($topic) OR toLower(c.description) CONTAINS toLower($topic))
            OPTIONAL MATCH (c)-[r]->(related)
            WHERE related.workspace_id = $workspace_id
            RETURN 
                c.name as concept,
                c.type as type,
                c.description as description,
                size(c.episode_ids) as episode_count,
                c.episode_ids as episode_ids,
                collect(DISTINCT {{rel: type(r), target: related.name}})[0..5] as relationships
            ORDER BY episode_count DESC
            LIMIT 20
            """
        
        # Pattern 6: "What practices optimize X?" (original, but enhanced)
        if "practice" in question_lower and "optimize" in question_lower:
            concept = self._extract_concept(question)
            return f"""
            MATCH (p:Practice)-[r:OPTIMIZES]->(c)
            WHERE c.workspace_id = $workspace_id
              AND (c.name CONTAINS $concept OR c.id CONTAINS $concept)
            RETURN p.name as practice, c.name as concept, r.description as description
            LIMIT 20
            """
        
        # Pattern: "What concepts are related to X?"
        if "concept" in question_lower and "relat" in question_lower:
            concept = self._extract_concept(question)
            return f"""
            MATCH (c1)-[r]->(c2)
            WHERE c1.workspace_id = $workspace_id
              AND c2.workspace_id = $workspace_id
              AND (c1.name CONTAINS $concept OR c1.id CONTAINS $concept)
            RETURN c1.name as source, type(r) as relationship, c2.name as target, r.description as description
            LIMIT 20
            """
        
        # Pattern: "What quotes about X?"
        if "quote" in question_lower:
            concept = self._extract_concept(question)
            return f"""
            MATCH (q:Quote)-[:ABOUT]->(c)
            WHERE c.workspace_id = $workspace_id
              AND (c.name CONTAINS $concept OR c.id CONTAINS $concept)
            RETURN q.text as quote, q.speaker as speaker, c.name as concept
            LIMIT 20
            """
        
        # Pattern: "What concepts appear in multiple episodes?"
        if "multiple episode" in question_lower or "cross episode" in question_lower or ("episode" in question_lower and "multiple" in question_lower):
            return f"""
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND c.episode_ids IS NOT NULL
              AND size(c.episode_ids) >= 2
            RETURN c.name as concept, c.type as type, size(c.episode_ids) as episode_count, 
                   c.description as description, c.episode_ids as episode_ids, c.source_paths as source_paths
            ORDER BY episode_count DESC
            LIMIT 20
            """
        
        # Pattern: "Who is X?" or "What is X?" - Entity lookup
        if question_lower.startswith(("who is ", "what is ", "tell me about ", "who are ", "what are ")):
            entity = question_lower.replace("who is ", "").replace("what is ", "").replace("tell me about ", "").replace("who are ", "").replace("what are ", "").strip()
            # Remove question marks and extra words
            entity = entity.split("?")[0].split(".")[0].strip()
            return f"""
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND (c.name =~ $entity_pattern OR c.name CONTAINS $entity_name)
            OPTIONAL MATCH (c)-[r1]->(related)
            WHERE related.workspace_id = $workspace_id
            OPTIONAL MATCH (related_to)-[r2]->(c)
            WHERE related_to.workspace_id = $workspace_id
            RETURN DISTINCT
                c.name as name,
                c.type as type,
                c.description as description,
                collect(DISTINCT {{rel: type(r1), target: related.name}})[0..5] as relationships_out,
                collect(DISTINCT {{rel: type(r2), source: related_to.name}})[0..5] as relationships_in,
                c.episode_ids as episode_ids,
                c.source_paths as source_paths,
                c.timestamps as timestamps
            LIMIT 1
            """
        
        # Pattern: "What concepts are mentioned?" or "List concepts"
        if "concept" in question_lower and ("mention" in question_lower or "list" in question_lower or "what" in question_lower):
            return f"""
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND (c:Concept OR c:Practice OR c:CognitiveState OR c:BehavioralPattern 
                   OR c:Principle OR c:Outcome OR c:Causality OR c:Person 
                   OR c:Place OR c:Organization OR c:Event)
            RETURN c.name as concept, c.type as type, c.description as description
            ORDER BY c.name
            LIMIT 50
            """
        
        # Pattern: Search for specific entity by name (if question contains capitalized words or specific terms)
        # Extract potential entity names (capitalized words or quoted strings)
        import re
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', question)
        if capitalized_words:
            # Use the first capitalized phrase as entity name
            entity_name = capitalized_words[0]
            return f"""
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND (c.name CONTAINS $entity_name OR c.name =~ $entity_pattern)
            OPTIONAL MATCH (c)-[r]->(related)
            WHERE related.workspace_id = $workspace_id
            RETURN DISTINCT
                c.name as name,
                c.type as type,
                c.description as description,
                collect(DISTINCT {{rel: type(r), target: related.name}})[0..10] as relationships
            LIMIT 5
            """
        
        # Default: Search for concepts matching question keywords
        # Extract meaningful keywords (remove stop words)
        stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why", "hi", "hello", "hey", "in", "on", "at", "to", "for", "of", "with"}
        keywords = [w for w in question.split() if w.lower() not in stop_words and len(w) > 2]
        
        if not keywords:
            # If no keywords, return general concept list
            return f"""
            MATCH (c)
            WHERE c.workspace_id = $workspace_id
              AND (c:Concept OR c:Practice OR c:Person)
            RETURN c.name as concept, c.type as type, c.episode_ids as episode_ids
            ORDER BY c.name
            LIMIT 20
            """
        
        # Search with keywords - use case-insensitive contains
        return f"""
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
          AND (
            ANY(keyword IN $keywords WHERE toLower(c.name) CONTAINS toLower(keyword))
            OR ANY(keyword IN $keywords WHERE toLower(c.description) CONTAINS toLower(keyword))
          )
        RETURN c.name as concept, c.type as type, c.description as description, 
               c.episode_ids as episode_ids, c.source_paths as source_paths
        ORDER BY c.name
        LIMIT 20
        """

    def _extract_concept(self, question: str) -> str:
        """
        Extract concept name from question (simple heuristic).

        Args:
            question: Natural language question

        Returns:
            Extracted concept name
        """
        # Simple extraction - can be improved with NLP
        words = question.split()
        # Remove common question words
        stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who"}
        concepts = [w for w in words if w.lower() not in stop_words]
        return " ".join(concepts[-3:])  # Last 3 words as concept
    
    def _extract_two_concepts(self, question: str) -> tuple[str, str]:
        """
        Extract two concepts from "How does X relate to Y?" pattern.
        
        Args:
            question: Natural language question
            
        Returns:
            Tuple of (concept_x, concept_y)
        """
        import re
        # Pattern: "How does X relate to Y?"
        match = re.search(r'how does (.+?) relate to (.+?)[?\.]', question.lower())
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # Fallback: split on "relate to"
        if "relate to" in question.lower():
            parts = question.lower().split("relate to")
            if len(parts) == 2:
                x = parts[0].replace("how does", "").replace("how do", "").strip()
                y = parts[1].replace("?", "").strip()
                return x, y
        
        # Default: return last two meaningful words
        words = [w for w in question.split() if len(w) > 2]
        if len(words) >= 2:
            return words[-2], words[-1]
        return "concept", "concept"
    
    def _extract_outcome_from_question(self, question: str) -> str:
        """
        Extract outcome from questions like "improving clarity", "reduce anxiety".
        
        Args:
            question: Natural language question
            
        Returns:
            Outcome name
        """
        import re
        # Pattern: "improving X" or "improve X"
        match = re.search(r'(?:improving|improve|optimize|enable)\s+(\w+(?:\s+\w+)*)', question.lower())
        if match:
            return match.group(1).strip()
        
        # Pattern: "associated with X" or "most associated with X"
        match = re.search(r'(?:associated with|most associated with)\s+(\w+(?:\s+\w+)*)', question.lower())
        if match:
            return match.group(1).strip()
        
        # Fallback: extract after "improving" or "improve"
        if "improving" in question.lower():
            idx = question.lower().index("improving")
            outcome = question[idx + len("improving"):].strip()
            outcome = outcome.split("?")[0].split(".")[0].strip()
            return outcome
        
        # Default: return last meaningful word
        words = [w for w in question.split() if len(w) > 2]
        return words[-1] if words else "outcome"
    
    def _extract_speaker_and_concept(self, question: str) -> tuple[str, str]:
        """
        Extract speaker and concept from "What did Speaker A emphasize about X?".
        
        Args:
            question: Natural language question
            
        Returns:
            Tuple of (speaker, concept)
        """
        import re
        # Pattern: "What did X consistently emphasize about Y?"
        match = re.search(r'what did (.+?) (?:consistently )?emphasize about (.+?)[?\.]', question.lower())
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # Pattern: "What did X emphasize about Y?"
        match = re.search(r'what did (.+?) emphasize (.+?)[?\.]', question.lower())
        if match:
            speaker = match.group(1).strip()
            concept = match.group(2).replace("about", "").strip()
            return speaker, concept
        
        # Fallback: extract capitalized name as speaker, last word as concept
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', question)
        words = [w for w in question.split() if len(w) > 2]
        speaker = capitalized[0] if capitalized else "speaker"
        concept = words[-1] if words else "concept"
        return speaker, concept
    
    def _extract_problem_from_question(self, question: str) -> str:
        """
        Extract problem from "reduce X" or "overcome X" questions.
        
        Args:
            question: Natural language question
            
        Returns:
            Problem name
        """
        import re
        # Pattern: "reduce X" or "overcome X"
        match = re.search(r'(?:reduce|overcome|overcoming)\s+(\w+(?:\s+\w+)*)', question.lower())
        if match:
            return match.group(1).strip()
        
        # Fallback: extract after "reduce" or "overcome"
        for word in ["reduce", "overcome", "overcoming"]:
            if word in question.lower():
                idx = question.lower().index(word)
                problem = question[idx + len(word):].strip()
                problem = problem.split(",")[0].split("?")[0].strip()
                return problem
        
        return "problem"
    
    def _extract_topic_after_about(self, question: str) -> str:
        """
        Extract topic from "about X" pattern.
        
        Args:
            question: Natural language question
            
        Returns:
            Topic name
        """
        import re
        # Pattern: "about X"
        match = re.search(r'about\s+(\w+(?:\s+\w+)*)', question.lower())
        if match:
            return match.group(1).strip()
        
        # Fallback: extract after "about"
        if "about" in question.lower():
            idx = question.lower().index("about")
            topic = question[idx + len("about"):].strip()
            topic = topic.split("?")[0].split(".")[0].strip()
            return topic
        
        return "topic"

    def execute_query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute Cypher query safely.

        Args:
            cypher: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records
        """
        # Validate query (prevent dangerous operations)
        if self._is_dangerous_query(cypher):
            raise ValueError("Query contains dangerous operations")
        
        params = parameters or {}
        params.setdefault("workspace_id", self.workspace_id)
        
        # Extract parameters from query if needed
        if "$query" in cypher and "query" not in params:
            # Extract search term from question
            question_words = cypher.split("$query")[0] if "$query" in cypher else ""
            # Use a default search term
            params["query"] = question_words.split()[-1] if question_words.split() else ""
        
        if "$pattern" in cypher and "pattern" not in params:
            # Create regex pattern from keywords
            params["pattern"] = "(?i).*" + params.get("query", "") + ".*"
        
        # Handle entity_name parameter for "who is X" queries
        if "$entity_name" in cypher and "entity_name" not in params:
            question = getattr(self, "_last_question", "").lower()
            if question.startswith(("who is ", "what is ", "tell me about ", "who are ", "what are ")):
                entity = question.replace("who is ", "").replace("what is ", "").replace("tell me about ", "").replace("who are ", "").replace("what are ", "").strip()
                entity = entity.split("?")[0].split(".")[0].strip()
                params["entity_name"] = entity
                params["entity_pattern"] = f"(?i).*{entity}.*"
            else:
                # Try to extract from capitalized words
                import re
                capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', getattr(self, "_last_question", ""))
                if capitalized:
                    params["entity_name"] = capitalized[0]
                    params["entity_pattern"] = f"(?i).*{capitalized[0]}.*"
                else:
                    params["entity_name"] = ""
                    params["entity_pattern"] = ".*"
        
        if "$entity_pattern" in cypher and "entity_pattern" not in params:
            entity = params.get("entity_name", "")
            if entity:
                params["entity_pattern"] = f"(?i).*{entity}.*"
            else:
                params["entity_pattern"] = ".*"
        
        # Handle keywords parameter (array)
        if "$keywords" in cypher and "keywords" not in params:
            # Extract keywords from stored question
            import re
            stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why"}
            question = getattr(self, "_last_question", "")
            keywords = [w for w in re.findall(r'\b\w+\b', question) 
                       if w.lower() not in stop_words and len(w) > 2]
            params["keywords"] = keywords[:5] if keywords else [""]
        
        # Handle new parameters for enhanced patterns
        if "$concept_x" in cypher and "concept_x" not in params:
            x, y = self._extract_two_concepts(getattr(self, "_last_question", ""))
            params["concept_x"] = x
            params["concept_y"] = y
            # Extract keywords for flexible matching
            import re
            stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why"}
            params["x_keywords"] = [w for w in re.findall(r'\b\w+\b', x) 
                                    if w.lower() not in stop_words and len(w) > 2]
            params["y_keywords"] = [w for w in re.findall(r'\b\w+\b', y) 
                                    if w.lower() not in stop_words and len(w) > 2]
        
        if "$concept_y" in cypher and "concept_y" not in params:
            x, y = self._extract_two_concepts(getattr(self, "_last_question", ""))
            params["concept_x"] = x
            params["concept_y"] = y
            # Extract keywords for flexible matching
            import re
            stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why"}
            params["x_keywords"] = [w for w in re.findall(r'\b\w+\b', x) 
                                    if w.lower() not in stop_words and len(w) > 2]
            params["y_keywords"] = [w for w in re.findall(r'\b\w+\b', y) 
                                    if w.lower() not in stop_words and len(w) > 2]
        
        if "$x_keywords" in cypher and "x_keywords" not in params:
            x, y = self._extract_two_concepts(getattr(self, "_last_question", ""))
            import re
            stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why"}
            params["x_keywords"] = [w for w in re.findall(r'\b\w+\b', x) 
                                    if w.lower() not in stop_words and len(w) > 2]
            params["y_keywords"] = [w for w in re.findall(r'\b\w+\b', y) 
                                    if w.lower() not in stop_words and len(w) > 2]
        
        if "$y_keywords" in cypher and "y_keywords" not in params:
            x, y = self._extract_two_concepts(getattr(self, "_last_question", ""))
            import re
            stop_words = {"what", "are", "is", "the", "a", "an", "that", "which", "who", "how", "when", "where", "why"}
            params["x_keywords"] = [w for w in re.findall(r'\b\w+\b', x) 
                                    if w.lower() not in stop_words and len(w) > 2]
            params["y_keywords"] = [w for w in re.findall(r'\b\w+\b', y) 
                                    if w.lower() not in stop_words and len(w) > 2]
        
        if "$outcome" in cypher and "outcome" not in params:
            params["outcome"] = self._extract_outcome_from_question(getattr(self, "_last_question", ""))
        
        if "$speaker" in cypher and "speaker" not in params:
            speaker, concept = self._extract_speaker_and_concept(getattr(self, "_last_question", ""))
            params["speaker"] = speaker
            params["concept"] = concept
        
        if "$concept" in cypher and "concept" not in params:
            # Try to extract from speaker query, or use generic extraction
            if "$speaker" in cypher:
                speaker, concept = self._extract_speaker_and_concept(getattr(self, "_last_question", ""))
                params["concept"] = concept
            else:
                params["concept"] = self._extract_concept(getattr(self, "_last_question", ""))
        
        if "$problem" in cypher and "problem" not in params:
            params["problem"] = self._extract_problem_from_question(getattr(self, "_last_question", ""))
        
        if "$topic" in cypher and "topic" not in params:
            params["topic"] = self._extract_topic_after_about(getattr(self, "_last_question", ""))
        
        try:
            results = self.client.execute_read(cypher, params)
            self.logger.info(
                "query_executed",
                extra={"context": {"result_count": len(results)}},
            )
            return results
        except Exception as e:
            self.logger.error(
                "query_execution_failed",
                exc_info=True,
                extra={"context": {"error": str(e), "query": cypher[:100]}},
            )
            raise

    def _is_dangerous_query(self, cypher: str) -> bool:
        """
        Check if query contains dangerous operations.

        Args:
            cypher: Cypher query string

        Returns:
            True if dangerous, False otherwise
        """
        dangerous_patterns = [
            "DELETE",
            "DROP",
            "DETACH DELETE",
            "CREATE CONSTRAINT",
            "CREATE INDEX",
            "REMOVE",
            "SET",
        ]
        
        cypher_upper = cypher.upper()
        # Allow SET in ON CREATE/MATCH clauses (safe)
        if "ON CREATE SET" in cypher_upper or "ON MATCH SET" in cypher_upper:
            return False
        
        return any(pattern in cypher_upper for pattern in dangerous_patterns)

