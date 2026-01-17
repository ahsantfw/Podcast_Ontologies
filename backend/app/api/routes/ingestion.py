"""
Ingestion Endpoints - Upload and process transcripts
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Header
from typing import Optional, List
from pydantic import BaseModel
import sys
from pathlib import Path
import uuid
import shutil

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.logging import get_logger
from backend.app.services.ingestion_service import process_transcripts_background
from backend.app.database.job_db import JobDB

logger = get_logger(__name__)

router = APIRouter()

class UploadResponse(BaseModel):
    upload_id: str
    files: list
    workspace_id: str

class ProcessRequest(BaseModel):
    upload_id: str
    workspace_id: Optional[str] = None
    clear_existing: bool = False

class ProcessResponse(BaseModel):
    job_id: str
    status: str
    upload_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    results: Optional[dict] = None
    error: Optional[str] = None

@router.post("/ingest/upload", response_model=UploadResponse)
async def upload_transcripts(
    files: List[UploadFile] = File(...),
    x_workspace_id: Optional[str] = Header(None)
):
    """Upload transcript files."""
    workspace_id = x_workspace_id or "default"
    upload_id = f"upload_{uuid.uuid4().hex[:12]}"
    
    # Create workspace directory if not exists
    workspace_dir = ROOT / "data" / "workspaces" / workspace_id / "transcripts"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    
    try:
        for file in files:
            # Save file
            file_path = workspace_dir / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            uploaded_files.append({
                "filename": file.filename,
                "size": file_path.stat().st_size,
                "status": "uploaded"
            })
        
        return UploadResponse(
            upload_id=upload_id,
            files=uploaded_files,
            workspace_id=workspace_id
        )
    except Exception as e:
        logger.error("upload_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/ingest/process", response_model=ProcessResponse)
async def process_transcripts(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    x_workspace_id: Optional[str] = Header(None)
):
    """Start processing uploaded transcripts (background job)."""
    workspace_id = request.workspace_id or x_workspace_id or "default"
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    # Create job status in database
    job_db = JobDB()
    job_db.create_job(
        job_id=job_id,
        workspace_id=workspace_id,
        job_type="processing",
        status="pending"
    )
    
    # Start background processing
    background_tasks.add_task(
        process_transcripts_background,
        job_id=job_id,
        workspace_id=workspace_id,
        upload_id=request.upload_id,
        clear_existing=request.clear_existing
    )
    
    return ProcessResponse(
        job_id=job_id,
        status="processing",
        upload_id=request.upload_id
    )

@router.get("/ingest/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get processing job status."""
    job_db = JobDB()
    job = job_db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0),
        results=job.get("results"),
        error=job.get("error")
    )

