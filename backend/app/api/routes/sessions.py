"""
Session Management Endpoints
"""

from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, List
from pydantic import BaseModel
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.app.database.session_db import SessionDB
from core_engine.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/sessions")
async def list_sessions(
    x_workspace_id: Optional[str] = Header(None),
    all_workspaces: Optional[bool] = Query(False)
):
    """List sessions. If all_workspaces=True, returns all sessions across workspaces."""
    workspace_id = x_workspace_id or "default"
    
    try:
        db = SessionDB()
        if all_workspaces:
            # Return all sessions across all workspaces
            sessions = db.get_all_sessions(limit=200)
        else:
            # Return only sessions for current workspace
            sessions = db.get_sessions_by_workspace(workspace_id)
        return {"workspace_id": workspace_id, "sessions": sessions}
    except Exception as e:
        logger.error("list_sessions_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details with message history."""
    try:
        db = SessionDB()
        session = db.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_session_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    try:
        db = SessionDB()
        success = db.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "deleted", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_session_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

