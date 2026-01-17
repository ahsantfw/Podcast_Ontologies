"""
Workspace Management Endpoints - Create, manage, delete workspaces
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.logging import get_logger
from backend.app.core.workspace import create_workspace_id
from qdrant_client import QdrantClient
import os

logger = get_logger(__name__)

router = APIRouter()

class WorkspaceCreate(BaseModel):
    name: Optional[str] = None

class WorkspaceResponse(BaseModel):
    workspace_id: str
    name: Optional[str] = None
    created_at: str

@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(request: WorkspaceCreate):
    """Create a new workspace."""
    workspace_id = create_workspace_id()
    
    # Create workspace directory
    workspace_dir = ROOT / "data" / "workspaces" / workspace_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "transcripts").mkdir(exist_ok=True)
    
    return WorkspaceResponse(
        workspace_id=workspace_id,
        name=request.name,
        created_at=str(Path().cwd())
    )

@router.delete("/workspaces/{workspace_id}/kg")
async def delete_kg(workspace_id: str):
    """Delete Knowledge Graph for workspace (keeps files, sessions, scripts)."""
    try:
        client = get_neo4j_client(workspace_id=workspace_id)
        
        # Delete all nodes and relationships with this workspace_id
        query = """
        MATCH (n)
        WHERE n.workspace_id = $workspace_id
        DETACH DELETE n
        """
        client.execute_write(query, {"workspace_id": workspace_id})
        
        client.close()
        
        return {"status": "deleted", "workspace_id": workspace_id, "what": "knowledge_graph"}
    except Exception as e:
        logger.error("delete_kg_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to delete KG: {str(e)}")

@router.delete("/workspaces/{workspace_id}/embeddings")
async def delete_embeddings(workspace_id: str):
    """Delete embeddings for workspace (keeps KG, files, sessions)."""
    try:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=qdrant_url)
        
        collection_name = f"{workspace_id}_chunks"
        
        # Delete collection if exists
        try:
            client.delete_collection(collection_name)
            return {"status": "deleted", "workspace_id": workspace_id, "what": "embeddings"}
        except Exception:
            # Collection doesn't exist
            return {"status": "not_found", "workspace_id": workspace_id, "what": "embeddings"}
            
    except Exception as e:
        logger.error("delete_embeddings_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to delete embeddings: {str(e)}")

@router.delete("/workspaces/{workspace_id}/all")
async def delete_all(workspace_id: str):
    """Delete KG + embeddings for workspace (keeps files, sessions, scripts)."""
    await delete_kg(workspace_id)
    await delete_embeddings(workspace_id)
    return {"status": "deleted", "workspace_id": workspace_id, "what": "kg_and_embeddings"}

@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """Delete entire workspace (everything including sessions)."""
    try:
        # Delete KG
        await delete_kg(workspace_id)
        
        # Delete embeddings
        await delete_embeddings(workspace_id)
        
        # Delete sessions
        from backend.app.database.session_db import SessionDB
        db = SessionDB()
        # Get all sessions for workspace
        sessions = db.get_sessions_by_workspace(workspace_id)
        for session in sessions:
            db.delete_session(session["session_id"])
        
        # Delete workspace directory
        workspace_dir = ROOT / "data" / "workspaces" / workspace_id
        if workspace_dir.exists():
            import shutil
            shutil.rmtree(workspace_dir)
        
        return {"status": "deleted", "workspace_id": workspace_id, "what": "entire_workspace"}
    except Exception as e:
        logger.error("delete_workspace_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to delete workspace: {str(e)}")

@router.get("/workspaces")
async def list_workspaces():
    """List all workspaces (from directories)."""
    import os
    from pathlib import Path
    
    ROOT = Path(__file__).resolve().parent.parent.parent.parent
    workspaces_dir = ROOT / "data" / "workspaces"
    
    workspaces = []
    if workspaces_dir.exists():
        for workspace_dir in workspaces_dir.iterdir():
            if workspace_dir.is_dir() and workspace_dir.name.startswith("workspace_"):
                workspaces.append({
                    "workspace_id": workspace_dir.name,
                    "name": workspace_dir.name,
                    "created_at": None  # TODO: Get from metadata if stored
                })
    
    # Always include default workspace
    if not any(w["workspace_id"] == "default" for w in workspaces):
        workspaces.insert(0, {
            "workspace_id": "default",
            "name": "default",
            "created_at": None
        })
    
    return {"workspaces": workspaces}

@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get workspace details."""
    return {
        "workspace_id": workspace_id,
        "name": workspace_id,
        "stats": {}  # TODO: Add stats
    }

