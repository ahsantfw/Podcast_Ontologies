"""
Query Endpoints - Natural language querying with workspace isolation
"""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from pydantic import BaseModel
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.reasoning import create_reasoner
from core_engine.logging import get_logger
from backend.app.core.workspace import get_workspace_id

logger = get_logger(__name__)

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    workspace_id: Optional[str] = None
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: list
    metadata: dict
    session_id: str

@router.post("/query", response_model=QueryResponse)
async def query_kg(request: QueryRequest, x_workspace_id: Optional[str] = Header(None)):
    """
    Query the Knowledge Graph.
    
    - **question**: Natural language question
    - **workspace_id**: Workspace identifier (from header or body)
    - **session_id**: Optional session ID for conversation context
    
    Returns: Answer, sources, metadata (RAG/KG breakdown)
    """
    workspace_id = request.workspace_id or x_workspace_id or "default"
    
    try:
        # Create reasoner with workspace isolation
        reasoner = create_reasoner(
            workspace_id=workspace_id,
            use_llm=True,
            use_hybrid=True
        )
        
        # Query with session context
        result = reasoner.query(
            question=request.question,
            session_id=request.session_id
        )
        
        reasoner.close()
        
        return QueryResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            metadata=result.get("metadata", {}),
            session_id=result.get("session_id", "")
        )
        
    except Exception as e:
        logger.error("query_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/query/history")
async def get_query_history(session_id: str, x_workspace_id: Optional[str] = Header(None)):
    """Get conversation history for a session."""
    workspace_id = x_workspace_id or "default"
    
    # TODO: Implement session history retrieval
    # For now, return empty
    return {
        "session_id": session_id,
        "workspace_id": workspace_id,
        "messages": []
    }

