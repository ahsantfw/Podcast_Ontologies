"""
Neo4j client for knowledge graph operations.
Handles connection, schema initialization, and basic utilities.
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

try:
    from neo4j import GraphDatabase, Driver, Session
except ImportError:
    raise ImportError(
        "neo4j package not installed. Install with: pip install neo4j"
    )

from core_engine.logging import get_logger


def load_env() -> None:
    """Load environment variables."""
    try:
        load_dotenv()
    except Exception:
        pass


def get_neo4j_config() -> Dict[str, Optional[str]]:
    """Get Neo4j configuration from environment."""
    load_env()
    # Support both NEO4J_USER and NEO4J_USERNAME
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": user,
        "password": os.getenv("NEO4J_PASSWORD", "password"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


class Neo4jClient:
    """Neo4j client wrapper for knowledge graph operations."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j connection URI (default: from env)
            user: Username (default: from env)
            password: Password (default: from env)
            database: Database name (default: from env)
            workspace_id: Workspace identifier for logging
        """
        config = get_neo4j_config()
        self.uri = uri or config["uri"]
        self.user = user or config["user"]
        self.password = password or config["password"]
        self.database = database or config["database"]
        self.workspace_id = workspace_id or "default"
        self.logger = get_logger("core_engine.kg", workspace_id=self.workspace_id)

        self._driver: Optional[Driver] = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Verify connection
            self._driver.verify_connectivity()
            self.logger.info(
                "neo4j_connected",
                extra={
                    "context": {
                        "uri": self.uri,
                        "database": self.database,
                    }
                },
            )
        except Exception as e:
            self.logger.error(
                "neo4j_connection_failed",
                exc_info=True,
                extra={"context": {"error": str(e), "uri": self.uri}},
            )
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            self.logger.info("neo4j_connection_closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def get_session(self) -> Session:
        """Get a Neo4j session."""
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")
        return self._driver.session(database=self.database)

    def execute_read(self, query: str, parameters: Optional[Dict[str, Any]] = None, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Execute a read query with retry on connection timeout.

        Args:
            query: Cypher query
            parameters: Query parameters
            max_retries: Maximum retry attempts on connection failure

        Returns:
            List of result records
        """
        for attempt in range(max_retries):
            try:
                with self.get_session() as session:
                    result = session.run(query, parameters or {})
                    return [record.data() for record in result]
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a connection/timeout error
                if any(keyword in error_str for keyword in ['timeout', 'connection', 'routing', 'unavailable']):
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            "neo4j_connection_retry",
                            extra={
                                "context": {
                                    "attempt": attempt + 1,
                                    "max_retries": max_retries,
                                    "error": str(e),
                                }
                            },
                        )
                        # Reconnect
                        try:
                            if self._driver:
                                self._driver.close()
                        except Exception:
                            pass
                        self._connect()
                        continue
                # If not a connection error or last attempt, raise
                raise
        # Should never reach here, but just in case
        raise RuntimeError("Failed to execute read query after retries")

    def execute_write(
        self, query: str, parameters: Optional[Dict[str, Any]] = None, max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Execute a write query with retry on connection timeout.

        Args:
            query: Cypher query
            parameters: Query parameters
            max_retries: Maximum retry attempts on connection failure

        Returns:
            List of result records
        """
        for attempt in range(max_retries):
            try:
                with self.get_session() as session:
                    result = session.run(query, parameters or {})
                    records = [record.data() for record in result]
                    return records
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a connection/timeout error
                if any(keyword in error_str for keyword in ['timeout', 'connection', 'routing', 'unavailable']):
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            "neo4j_connection_retry",
                            extra={
                                "context": {
                                    "attempt": attempt + 1,
                                    "max_retries": max_retries,
                                    "error": str(e),
                                }
                            },
                        )
                        # Reconnect
                        try:
                            if self._driver:
                                self._driver.close()
                        except Exception:
                            pass
                        self._connect()
                        continue
                # If not a connection error or last attempt, raise
                raise
        # Should never reach here, but just in case
        raise RuntimeError("Failed to execute write query after retries")

    def execute_write_batch(
        self, queries: List[tuple[str, Optional[Dict[str, Any]]]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Execute multiple write queries in a transaction.

        Args:
            queries: List of (query, parameters) tuples

        Returns:
            List of result lists (one per query)
        """
        results = []
        with self.get_session() as session:
            with session.begin_transaction() as tx:
                for query, parameters in queries:
                    result = tx.run(query, parameters or {})
                    records = [record.data() for record in result]
                    results.append(records)
                tx.commit()
            self.logger.info(
                "neo4j_batch_write_complete",
                extra={"context": {"queries": len(queries)}},
            )
        return results

    def test_connection(self) -> bool:
        """
        Test Neo4j connection.

        Returns:
            True if connection successful
        """
        try:
            result = self.execute_read("RETURN 1 as test")
            return len(result) > 0 and result[0].get("test") == 1
        except Exception as e:
            self.logger.error(
                "neo4j_connection_test_failed",
                exc_info=True,
                extra={"context": {"error": str(e)}},
            )
            return False


def get_neo4j_client(
    workspace_id: Optional[str] = None,
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
) -> Neo4jClient:
    """
    Get a Neo4j client instance.

    Args:
        workspace_id: Workspace identifier
        uri: Neo4j URI (optional, uses env if not provided)
        user: Username (optional, uses env if not provided)
        password: Password (optional, uses env if not provided)
        database: Database name (optional, uses env if not provided)

    Returns:
        Neo4jClient instance
    """
    return Neo4jClient(
        uri=uri,
        user=user,
        password=password,
        database=database,
        workspace_id=workspace_id,
    )

