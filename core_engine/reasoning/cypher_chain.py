"""
LangChain GraphCypherQAChain integration for natural language queries.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

try:
    from langchain.chains import GraphCypherQAChain
    from langchain_community.graphs import Neo4jGraph
    from langchain_openai import ChatOpenAI
except ImportError:
    GraphCypherQAChain = None
    Neo4jGraph = None
    ChatOpenAI = None

from core_engine.kg.neo4j_client import Neo4jClient
from core_engine.logging import get_logger


def load_env() -> None:
    """Load environment variables."""
    try:
        load_dotenv()
    except Exception:
        pass


class KGCypherChain:
    """LangChain GraphCypherQAChain wrapper for KG queries."""

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        workspace_id: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize KG Cypher chain.

        Args:
            neo4j_client: Neo4j client instance
            model: OpenAI model name
            temperature: LLM temperature
            workspace_id: Workspace identifier
            verbose: Whether to show verbose output
        """
        if GraphCypherQAChain is None:
            raise ImportError(
                "langchain and langchain_community packages required. "
                "Install with: pip install langchain langchain-community langchain-openai"
            )
        
        self.neo4j_client = neo4j_client
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger(
            "core_engine.reasoning.cypher_chain",
            workspace_id=self.workspace_id,
        )
        
        # Initialize LLM
        load_env()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )
        
        # Create Neo4jGraph from client
        self.graph = Neo4jGraph(
            url=neo4j_client.uri,
            username=neo4j_client.user,
            password=neo4j_client.password,
            database=neo4j_client.database,
        )
        
        # Create chain
        self.chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            verbose=verbose,
            allow_dangerous_requests=False,  # Safety: don't allow dangerous queries
            return_intermediate_steps=True,
        )
        
        self.logger.info("cypher_chain_initialized")

    def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query knowledge graph with natural language.

        Args:
            question: Natural language question
            context: Optional context (conversation history, etc.)

        Returns:
            Dictionary with answer and intermediate steps
        """
        try:
            # Add workspace context to question if needed
            enhanced_question = self._enhance_question(question, context)
            
            result = self.chain.invoke({"question": enhanced_question})
            
            self.logger.info(
                "query_completed",
                extra={"context": {"question": question[:100]}},
            )
            
            return {
                "answer": result.get("result", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "question": question,
            }
        except Exception as e:
            self.logger.error(
                "query_failed",
                exc_info=True,
                extra={"context": {"question": question[:100], "error": str(e)}},
            )
            raise

    def _enhance_question(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Enhance question with context.

        Args:
            question: Original question
            context: Optional context

        Returns:
            Enhanced question
        """
        if not context:
            return question
        
        # Add conversation history if available
        history = context.get("conversation_history", [])
        if history:
            history_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in history[-3:]  # Last 3 messages
            ])
            return f"Previous conversation:\n{history_text}\n\nCurrent question: {question}"
        
        return question

    def close(self) -> None:
        """Close connections."""
        if hasattr(self.graph, 'close'):
            self.graph.close()
        self.logger.info("cypher_chain_closed")


def create_cypher_chain(
    neo4j_client: Neo4jClient,
    model: str = "gpt-4o",
    workspace_id: Optional[str] = None,
) -> KGCypherChain:
    """
    Create a KG Cypher chain (convenience function).

    Args:
        neo4j_client: Neo4j client
        model: OpenAI model name
        workspace_id: Workspace identifier

    Returns:
        KGCypherChain instance
    """
    return KGCypherChain(
        neo4j_client=neo4j_client,
        model=model,
        workspace_id=workspace_id,
    )

