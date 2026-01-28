"""
FastAPI Application - Main Entry Point
Production-grade REST API for Knowledge Graph System
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# from fastapi.staticfiles import StaticFiles  # Not needed for React frontend
# from fastapi.templating import Jinja2Templates  # Not needed for React frontend
from dotenv import load_dotenv

# Add parent directory to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

load_dotenv()

from core_engine.logging import get_logger
from backend.app.core.reasoner_pool import get_reasoner_pool

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Graph API",
    description="REST API for Podcast Intelligence System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS - Enable for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP, allow all. Change later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (if needed for assets, but React handles its own static files)
# app.mount("/static", StaticFiles(directory=str(ROOT / "backend" / "app" / "static")), name="static")
# templates = Jinja2Templates(directory=str(ROOT / "backend" / "app" / "templates"))

# Import routes (fix imports to work from project root)
try:
    from backend.app.api.routes import query, scripts, ingestion, graph, workspace, sessions
except ImportError:
    # Fallback: import directly
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from api.routes import query, scripts, ingestion, graph, workspace, sessions

# Register routes
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(scripts.router, prefix="/api/v1", tags=["scripts"])
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(graph.router, prefix="/api/v1", tags=["graph"])
app.include_router(workspace.router, prefix="/api/v1", tags=["workspace"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])

# React frontend handles all page routes (/, /chat, /dashboard, etc.)
# Backend only serves API endpoints under /api/v1/*

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("app_startup")
    # Reasoner pool will be initialized on first use

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("app_shutdown")
    try:
        pool = get_reasoner_pool()
        pool.cleanup_all()
        logger.info("reasoner_pool_cleaned_up_on_shutdown")
    except Exception as e:
        logger.warning("reasoner_pool_cleanup_failed", extra={"error": str(e)})

@app.get("/api/v1/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error("unhandled_exception", exc_info=True, extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

