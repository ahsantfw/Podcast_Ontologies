"""
Workspace Management - Multi-user support via workspace_id
"""

from typing import Optional
from fastapi import Header, HTTPException
import uuid

def get_workspace_id(x_workspace_id: Optional[str] = Header(None)) -> str:
    """
    Extract workspace_id from header or use default.
    For MVP: If not provided, use 'default' workspace.
    Later: Can create workspace if not exists.
    """
    if x_workspace_id:
        return x_workspace_id
    return "default"

def create_workspace_id() -> str:
    """Generate new workspace ID."""
    return f"workspace_{uuid.uuid4().hex[:12]}"

