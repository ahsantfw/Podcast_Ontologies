"""
Query Endpoints - Natural language querying with workspace isolation
"""

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from pydantic import BaseModel
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.reasoning import create_reasoner
from core_engine.logging import get_logger
from backend.app.core.workspace import get_workspace_id
from backend.app.core.reasoner_pool import get_reasoner_pool

logger = get_logger(__name__)

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    workspace_id: Optional[str] = None
    session_id: Optional[str] = None
    style: Optional[str] = "casual"
    tone: Optional[str] = "warm"

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
        # Get reasoner from pool (reused across requests for same workspace)
        reasoner_pool = get_reasoner_pool()
        reasoner = reasoner_pool.get_reasoner(
            workspace_id=workspace_id,
            use_llm=True,
            use_hybrid=True
        )
        
        # Query with session context and style/tone
        result = reasoner.query(
            question=request.question,
            session_id=request.session_id,
            style=request.style or "casual",
            tone=request.tone or "warm"
        )
        
        # NOTE: Don't close reasoner - it's reused from pool
        # Pool will handle cleanup automatically
        
        return QueryResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            metadata=result.get("metadata", {}),
            session_id=result.get("session_id", "")
        )
        
    except Exception as e:
        logger.error("query_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.post("/query/stream")
async def query_kg_stream(request: QueryRequest, x_workspace_id: Optional[str] = Header(None)):
    """
    Query the Knowledge Graph with streaming response.
    
    Returns Server-Sent Events (SSE) stream with answer chunks.
    """
    workspace_id = request.workspace_id or x_workspace_id or "default"
    
    async def generate_stream():
        """Async generator function for streaming response."""
        import asyncio
        from queue import Queue
        from threading import Thread
        
        try:
            # Get reasoner from pool
            reasoner_pool = get_reasoner_pool()
            reasoner = reasoner_pool.get_reasoner(
                workspace_id=workspace_id,
                use_llm=True,
                use_hybrid=True
            )
            
            # Queue to pass chunks from sync generator to async generator
            chunk_queue = Queue()
            exception_queue = Queue()
            
            def run_stream():
                """Run sync generator in thread and put chunks in queue."""
                try:
                    for chunk_data in reasoner.query_streaming(
                        question=request.question,
                        session_id=request.session_id,
                        style=request.style or "casual",
                        tone=request.tone or "warm"
                    ):
                        # Put chunk in queue (blocking with timeout to prevent queue overflow)
                        chunk_queue.put(chunk_data, block=True, timeout=1.0)
                    chunk_queue.put(None)  # Signal completion
                except Exception as e:
                    exception_queue.put(e)
            
            # Start streaming in background thread
            stream_thread = Thread(target=run_stream, daemon=True)
            stream_thread.start()
            
            # Yield chunks as they arrive
            timeout_count = 0
            max_timeout = 300  # 30 seconds max wait
            
            while True:
                # Check for exceptions
                if not exception_queue.empty():
                    raise exception_queue.get()
                
                # Get chunk from queue (with short timeout for responsive streaming)
                try:
                    chunk_data = chunk_queue.get(timeout=0.05)  # 50ms timeout for responsive streaming
                    timeout_count = 0  # Reset timeout counter
                except:
                    # Timeout - check if thread is still alive
                    timeout_count += 1
                    if timeout_count > max_timeout:
                        logger.warning("stream_timeout", extra={"context": {"workspace_id": workspace_id}})
                        break
                    
                    if not stream_thread.is_alive():
                        if not exception_queue.empty():
                            raise exception_queue.get()
                        break
                    # Small sleep to avoid busy-waiting
                    await asyncio.sleep(0.01)  # 10ms sleep for CPU efficiency
                    continue
                
                # None signals completion
                if chunk_data is None:
                    break
                
                # Format as SSE
                chunk = chunk_data.get("chunk", "")
                done = chunk_data.get("done", False)
                
                # Send chunk immediately (no delay for faster streaming)
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                
                # Send final metadata when done
                if done:
                    final_data = {
                        "chunk": "",
                        "done": True,
                        "session_id": chunk_data.get("session_id", ""),
                        "sources": chunk_data.get("sources", []),
                        "metadata": chunk_data.get("metadata", {"method": "agent_streaming"})
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    break
                    
        except Exception as e:
            logger.error("query_stream_failed", exc_info=True, extra={"error": str(e)})
            error_data = {
                "chunk": f"Error: {str(e)}",
                "done": True,
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )

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

