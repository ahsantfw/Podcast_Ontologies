"""
Session Database - SQLite for session storage
"""

import sqlite3
import json
from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = ROOT / "data" / "sessions.db"

class SessionDB:
    """Session database manager."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                messages TEXT,  -- JSON array
                metadata TEXT   -- JSON object
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_workspace 
            ON sessions(workspace_id)
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, workspace_id: str, metadata: dict = None):
        """Create a new session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, workspace_id, messages, metadata)
            VALUES (?, ?, ?, ?)
        """, (
            session_id,
            workspace_id,
            json.dumps([]),
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def add_message(self, session_id: str, role: str, content: str, metadata: dict = None):
        """Add message to session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get existing messages
        cursor.execute("SELECT messages FROM sessions WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        
        if result:
            messages = json.loads(result[0])
        else:
            messages = []
        
        # Add new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        messages.append(message)
        
        # Update
        cursor.execute("""
            UPDATE sessions 
            SET messages = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (json.dumps(messages), session_id))
        
        conn.commit()
        conn.close()
    
    def get_session(self, session_id: str) -> dict:
        """Get session by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, workspace_id, created_at, updated_at, messages, metadata
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            "session_id": result[0],
            "workspace_id": result[1],
            "created_at": result[2],
            "updated_at": result[3],
            "messages": json.loads(result[4]) if result[4] else [],
            "metadata": json.loads(result[5]) if result[5] else {}
        }
    
    def get_sessions_by_workspace(self, workspace_id: str) -> list:
        """Get all sessions for workspace."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, workspace_id, created_at, updated_at
            FROM sessions
            WHERE workspace_id = ?
            ORDER BY updated_at DESC
            LIMIT 100
        """, (workspace_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "session_id": r[0],
                "workspace_id": r[1],
                "created_at": r[2],
                "updated_at": r[3]
            }
            for r in results
        ]
    
    def get_all_sessions(self, limit: int = 200) -> list:
        """Get all sessions across all workspaces."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, workspace_id, created_at, updated_at
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "session_id": r[0],
                "workspace_id": r[1],
                "created_at": r[2],
                "updated_at": r[3]
            }
            for r in results
        ]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted

