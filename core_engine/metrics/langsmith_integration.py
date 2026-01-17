"""
LangSmith integration for observability and tracing.

LangSmith provides:
- Automatic tracing of LLM calls
- Cost tracking
- Performance monitoring
- Debugging tools
- Dashboards and alerts

Setup:
1. Install: pip install langsmith
2. Set env vars:
   - LANGCHAIN_API_KEY (get from https://smith.langchain.com)
   - LANGCHAIN_TRACING_V2=true
   - LANGCHAIN_PROJECT=<your-project-name>
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    from langsmith import traceable, Client
    from langchain_core.tracers import LangChainTracer
    from langchain_core.callbacks import CallbackManager
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    traceable = None
    Client = None
    LangChainTracer = None
    CallbackManager = None


def is_langsmith_enabled() -> bool:
    """Check if LangSmith is enabled via environment variables."""
    return (
        LANGSMITH_AVAILABLE
        and os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
        and os.getenv("LANGCHAIN_API_KEY") is not None
    )


def get_langsmith_client() -> Optional[Client]:
    """Get LangSmith client if available."""
    if not is_langsmith_enabled():
        return None
    try:
        return Client()
    except Exception:
        return None


def get_langchain_callback_manager() -> Optional[CallbackManager]:
    """
    Get LangChain callback manager with LangSmith tracer.
    Use this with LangChain components to enable automatic tracing.
    """
    if not is_langsmith_enabled():
        return None
    
    try:
        tracer = LangChainTracer()
        return CallbackManager([tracer])
    except Exception:
        return None


@contextmanager
def langsmith_run(
    name: str,
    run_type: str = "chain",
    inputs: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list] = None,
):
    """
    Context manager for LangSmith tracing.
    
    Usage:
        with langsmith_run("extract_kg", inputs={"chunks": len(chunks)}):
            # Your code here
            result = extract_kg(chunks)
    
    Args:
        name: Name of the run
        run_type: Type of run (chain, tool, llm, etc.)
        inputs: Input data for the run
        metadata: Additional metadata
        tags: Tags for filtering/grouping
    """
    if not is_langsmith_enabled() or traceable is None:
        # If LangSmith not available, just execute the code
        yield
        return
    
    # Use traceable decorator as context manager
    @traceable(name=name, run_type=run_type)
    def _run():
        pass
    
    # Start the run
    run = _run()
    
    try:
        # Update run with inputs/metadata if client available
        client = get_langsmith_client()
        if client and run:
            if inputs:
                client.update_run(run.id, inputs=inputs)
            if metadata:
                client.update_run(run.id, metadata=metadata)
            if tags:
                client.update_run(run.id, tags=tags)
        
        yield run
    finally:
        # Run completes when context exits
        pass


def trace_operation(
    name: str,
    run_type: str = "chain",
    inputs: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list] = None,
):
    """
    Decorator for tracing operations with LangSmith.
    
    Usage:
        @trace_operation("extract_kg", metadata={"workspace": "default"})
        def extract_kg(chunks):
            # Your code
            return result
    """
    if not is_langsmith_enabled() or traceable is None:
        # If LangSmith not available, return identity decorator
        def identity_decorator(func):
            return func
        return identity_decorator
    
    return traceable(
        name=name,
        run_type=run_type,
        inputs=inputs,
        metadata=metadata,
        tags=tags,
    )


def log_feedback(
    run_id: str,
    score: float,
    comment: Optional[str] = None,
    source: str = "user",
):
    """
    Log feedback for a LangSmith run.
    
    Args:
        run_id: LangSmith run ID
        score: Score (0-1 or -1 to 1)
        comment: Optional comment
        source: Source of feedback (user, automated, etc.)
    """
    if not is_langsmith_enabled():
        return
    
    client = get_langsmith_client()
    if client:
        try:
            client.create_feedback(
                run_id=run_id,
                score=score,
                comment=comment,
                source=source,
            )
        except Exception:
            pass  # Silently fail if feedback logging fails


def get_run_url(run_id: str) -> Optional[str]:
    """Get URL to view a run in LangSmith UI."""
    if not is_langsmith_enabled():
        return None
    
    project = os.getenv("LANGCHAIN_PROJECT", "default")
    api_url = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    base_url = api_url.replace("/api", "")
    
    return f"{base_url}/o/{os.getenv('LANGCHAIN_TENANT_ID', 'default')}/projects/p/{project}/r/{run_id}"


def setup_langsmith(
    api_key: str,
    project: str = "ontology-ingestion",
    endpoint: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """
    Setup LangSmith environment variables.
    
    Args:
        api_key: LangSmith API key
        project: Project name
        endpoint: Optional custom endpoint
        tenant_id: Optional tenant ID
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    
    if endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    if tenant_id:
        os.environ["LANGCHAIN_TENANT_ID"] = tenant_id


# Example usage functions
def example_traced_extraction():
    """Example of how to trace KG extraction."""
    from core_engine.kg.extractor import KGExtractor
    from langchain_core.documents import Document
    
    # Option 1: Use decorator
    @trace_operation(
        "extract_kg_batch",
        metadata={"model": "gpt-4o", "batch_size": 5},
        tags=["kg-extraction", "ingestion"]
    )
    def extract_with_tracing(chunks):
        extractor = KGExtractor(model="gpt-4o", batch_size=5)
        return extractor.extract_from_chunks(chunks)
    
    # Option 2: Use context manager
    chunks = [Document(page_content="...", metadata={})]
    with langsmith_run(
        "extract_kg",
        inputs={"chunk_count": len(chunks)},
        metadata={"workspace": "default"},
        tags=["kg-extraction"]
    ):
        extractor = KGExtractor(model="gpt-4o", batch_size=5)
        result = extractor.extract_from_chunks(chunks)
    
    return result


def example_traced_embeddings():
    """Example of how to trace embeddings."""
    from openai import OpenAI
    
    @trace_operation(
        "create_embeddings",
        metadata={"model": "text-embedding-3-large"},
        tags=["embeddings", "ingestion"]
    )
    def embed_with_tracing(texts):
        client = OpenAI()
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=texts
        )
        return [item.embedding for item in response.data]
    
    return embed_with_tracing(["text1", "text2"])

