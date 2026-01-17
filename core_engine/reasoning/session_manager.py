"""
Session management with memory and context tracking.
Handles conversation sessions, memory management, and context preservation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import deque
import json

from core_engine.logging import get_logger
import sys
from pathlib import Path

# Import SessionDB for persistence
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

try:
    from backend.app.database.session_db import SessionDB
    SESSION_DB_AVAILABLE = True
except ImportError:
    SESSION_DB_AVAILABLE = False


@dataclass
class Message:
    """Single message in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class QuerySession:
    """A query session with conversation history and context."""
    session_id: str
    workspace_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: deque = field(default_factory=lambda: deque(maxlen=50))  # Max 50 messages
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure messages is a deque."""
        if not isinstance(self.messages, deque):
            self.messages = deque(self.messages, maxlen=50)

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the session."""
        message = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # Auto-save to database after adding message (if session_db is available)
        # We'll save the entire session to keep it in sync

    def get_conversation_history(self, max_messages: Optional[int] = None) -> List[Message]:
        """Get conversation history."""
        messages = list(self.messages)
        if max_messages:
            return messages[-max_messages:]
        return messages

    def get_recent_context(self, max_messages: int = 5) -> str:
        """Get recent conversation context as text."""
        recent = self.get_conversation_history(max_messages=max_messages)
        context_parts = []
        for msg in recent:
            context_parts.append(f"{msg.role.upper()}: {msg.content}")
        return "\n".join(context_parts)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages.clear()
        self.context.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuerySession:
        """Create from dictionary."""
        messages = deque(
            [Message.from_dict(msg) for msg in data.get("messages", [])],
            maxlen=50
        )
        return cls(
            session_id=data["session_id"],
            workspace_id=data["workspace_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=messages,
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """Manages query sessions with memory and cleanup."""

    def __init__(
        self,
        workspace_id: Optional[str] = None,
        max_sessions: int = 1000,
        session_timeout: timedelta = timedelta(hours=24),
        cleanup_interval: timedelta = timedelta(hours=1),
    ):
        """
        Initialize session manager.

        Args:
            workspace_id: Workspace identifier
            max_sessions: Maximum number of active sessions
            session_timeout: Time before session expires
            cleanup_interval: How often to run cleanup
        """
        self.workspace_id = workspace_id or "default"
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        
        self.sessions: Dict[str, QuerySession] = {}
        self.last_cleanup: datetime = datetime.now()
        self.logger = get_logger(
            "core_engine.reasoning.session_manager",
            workspace_id=self.workspace_id,
        )
        
        # Initialize SessionDB for persistence (if available)
        self.session_db = None
        if SESSION_DB_AVAILABLE:
            try:
                self.session_db = SessionDB()
                self.logger.info("session_db_initialized")
            except Exception as e:
                self.logger.warning("session_db_init_failed", extra={"error": str(e)})

    def create_session(
        self,
        session_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> QuerySession:
        """
        Create a new query session.

        Args:
            session_id: Optional session ID (generated if not provided)
            workspace_id: Optional workspace ID (uses default if not provided)

        Returns:
            New QuerySession instance
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        workspace = workspace_id or self.workspace_id
        
        # Check if we need cleanup
        self._maybe_cleanup()
        
        # Check if we're at max capacity
        if len(self.sessions) >= self.max_sessions:
            self.logger.warning(
                "max_sessions_reached",
                extra={"context": {"max_sessions": self.max_sessions}},
            )
            # Remove oldest session
            oldest_id = min(
                self.sessions.keys(),
                key=lambda sid: self.sessions[sid].updated_at,
            )
            del self.sessions[oldest_id]
        
        session = QuerySession(
            session_id=session_id,
            workspace_id=workspace,
        )
        
        self.sessions[session_id] = session
        
        # Persist to database if available
        if self.session_db:
            try:
                self.session_db.create_session(
                    session_id=session_id,
                    workspace_id=workspace,
                    metadata=session.metadata
                )
            except Exception as e:
                self.logger.warning("session_create_in_db_failed", extra={
                    "context": {"session_id": session_id, "error": str(e)}
                })
        
        self.logger.info(
            "session_created",
            extra={"context": {"session_id": session_id, "workspace_id": workspace}},
        )
        
        return session

    def get_session(self, session_id: str) -> Optional[QuerySession]:
        """
        Get an existing session from memory or database.

        Args:
            session_id: Session ID

        Returns:
            QuerySession if found, None otherwise
        """
        # First check in-memory cache
        session = self.sessions.get(session_id)
        if session:
            # Check if expired
            if (datetime.now() - session.updated_at) > self.session_timeout:
                self.logger.warning(
                    "session_expired",
                    extra={"context": {"session_id": session_id}},
                )
                del self.sessions[session_id]
                return None
            return session
        
        # If not in memory, try to load from database
        if self.session_db:
            try:
                db_session = self.session_db.get_session(session_id)
                if db_session and db_session.get("workspace_id") == self.workspace_id:
                    # Restore session from database
                    messages = db_session.get("messages", [])
                    
                    # Parse datetime strings
                    created_at = db_session.get("created_at")
                    if isinstance(created_at, str):
                        try:
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            created_at = datetime.now()
                    elif not isinstance(created_at, datetime):
                        created_at = datetime.now()
                    
                    updated_at = db_session.get("updated_at")
                    if isinstance(updated_at, str):
                        try:
                            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        except:
                            updated_at = datetime.now()
                    elif not isinstance(updated_at, datetime):
                        updated_at = datetime.now()
                    
                    restored_session = QuerySession(
                        session_id=session_id,
                        workspace_id=db_session["workspace_id"],
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                    
                    # Restore messages
                    for msg_data in messages:
                        try:
                            if isinstance(msg_data, dict):
                                msg = Message.from_dict(msg_data)
                                restored_session.messages.append(msg)
                        except Exception as e:
                            self.logger.warning("message_restore_failed", extra={
                                "context": {"session_id": session_id, "error": str(e)}
                            })
                    
                    # Restore metadata
                    restored_session.metadata = db_session.get("metadata", {})
                    
                    # Cache in memory
                    self.sessions[session_id] = restored_session
                    
                    self.logger.info("session_loaded_from_db", extra={
                        "context": {
                            "session_id": session_id,
                            "message_count": len(messages)
                        }
                    })
                    return restored_session
            except Exception as e:
                self.logger.warning("session_load_from_db_failed", exc_info=True, extra={
                    "context": {"session_id": session_id, "error": str(e)}
                })
        
        return None

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> QuerySession:
        """
        Get existing session or create new one.

        Args:
            session_id: Optional session ID
            workspace_id: Optional workspace ID

        Returns:
            QuerySession instance
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        return self.create_session(session_id=session_id, workspace_id=workspace_id)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(
                "session_deleted",
                extra={"context": {"session_id": session_id}},
            )
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now()
        expired_ids = [
            sid
            for sid, session in self.sessions.items()
            if now - session.updated_at > self.session_timeout
        ]
        
        for sid in expired_ids:
            del self.sessions[sid]
        
        if expired_ids:
            self.logger.info(
                "sessions_cleaned_up",
                extra={"context": {"count": len(expired_ids)}},
            )
        
        return len(expired_ids)

    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has passed."""
        if datetime.now() - self.last_cleanup > self.cleanup_interval:
            self.cleanup_expired_sessions()
            self.last_cleanup = datetime.now()

    def get_session_count(self) -> int:
        """Get current number of active sessions."""
        return len(self.sessions)

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dictionary with memory statistics
        """
        total_messages = sum(len(session.messages) for session in self.sessions.values())
        total_context_size = sum(
            len(str(session.context)) for session in self.sessions.values()
        )
        
        return {
            "active_sessions": len(self.sessions),
            "total_messages": total_messages,
            "total_context_size_bytes": total_context_size,
            "max_sessions": self.max_sessions,
            "session_timeout_hours": self.session_timeout.total_seconds() / 3600,
        }

    def save_session(self, session_id: str, filepath: str) -> bool:
        """
        Save session to file.

        Args:
            session_id: Session ID
            filepath: Path to save file

        Returns:
            True if saved successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        try:
            with open(filepath, 'w') as f:
                json.dump(session.to_dict(), f, indent=2, default=str)
            return True
        except Exception as e:
            self.logger.error(
                "session_save_failed",
                exc_info=True,
                extra={"context": {"session_id": session_id, "error": str(e)}},
            )
            return False

    def load_session(self, filepath: str) -> Optional[QuerySession]:
        """
        Load session from file.

        Args:
            filepath: Path to session file

        Returns:
            QuerySession if loaded successfully, None otherwise
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            session = QuerySession.from_dict(data)
            self.sessions[session.session_id] = session
            return session
        except Exception as e:
            self.logger.error(
                "session_load_failed",
                exc_info=True,
                extra={"context": {"filepath": filepath, "error": str(e)}},
            )
            return None

    def clear_all_sessions(self) -> int:
        """
        Clear all sessions.

        Returns:
            Number of sessions cleared
        """
        count = len(self.sessions)
        self.sessions.clear()
        self.logger.warning(
            "all_sessions_cleared",
            extra={"context": {"count": count}},
        )
        return count

