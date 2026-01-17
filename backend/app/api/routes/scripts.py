"""
Script Generation Endpoints
"""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional, List
from pydantic import BaseModel
import sys
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.script_generation.script_generator import ScriptGenerator
from core_engine.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

class ScriptGenerateRequest(BaseModel):
    theme: str
    workspace_id: Optional[str] = None
    episodes: Optional[List[str]] = None
    runtime_minutes: int = 45
    style: str = "tapestry"  # tapestry, thematic, linear
    max_quotes: int = 20
    format: str = "markdown"  # markdown, json, plain

class ScriptResponse(BaseModel):
    script_id: str
    title: str
    formatted: str
    metadata: dict

@router.post("/scripts/generate", response_model=ScriptResponse)
async def generate_script(request: ScriptGenerateRequest, x_workspace_id: Optional[str] = Header(None)):
    """Generate a tapestry-style script from Knowledge Graph."""
    workspace_id = request.workspace_id or x_workspace_id or "default"
    
    try:
        generator = ScriptGenerator(workspace_id=workspace_id)
        
        result = generator.generate(
            theme=request.theme,
            episodes=request.episodes,
            runtime_minutes=request.runtime_minutes,
            style=request.style,
            max_quotes=request.max_quotes,
            output_format=request.format
        )
        
        script_id = f"script_{uuid.uuid4().hex[:12]}"
        
        # Extract title from result
        title = result.get("script", {}).get("title", f"Script: {request.theme}")
        
        return ScriptResponse(
            script_id=script_id,
            title=title,
            formatted=result.get("formatted", ""),
            metadata=result.get("metadata", {})
        )
        
    except ValueError as e:
        # Handle "no quotes found" error more gracefully
        logger.warning("script_generation_no_quotes", exc_info=True, extra={"error": str(e), "theme": request.theme})
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("script_generation_failed", exc_info=True, extra={"error": str(e), "theme": request.theme})
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")

