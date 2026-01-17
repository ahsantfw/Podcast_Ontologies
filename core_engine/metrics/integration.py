"""
Integration helpers to add cost tracking to existing code.
Monkey-patches OpenAI client methods to automatically track costs.
"""

from __future__ import annotations

import time
from typing import Optional, Any
from openai import OpenAI

from core_engine.metrics.cost_tracker import get_cost_tracker


def patch_openai_client(client: OpenAI) -> OpenAI:
    """
    Patch OpenAI client to automatically track costs.
    This modifies the client in-place to add tracking.
    
    Args:
        client: OpenAI client instance
        
    Returns:
        Same client instance (modified in-place)
    """
    cost_tracker = get_cost_tracker()
    
    # Check if already patched (has _tracked attribute)
    if hasattr(client, "_tracked"):
        return client
    
    # Store original methods
    original_chat_create = client.chat.completions.create
    original_embeddings_create = client.embeddings.create
    
    def tracked_chat_create(*args, **kwargs):
        """Tracked chat.completions.create."""
        start_time = time.time()
        response = original_chat_create(*args, **kwargs)
        duration = time.time() - start_time
        
        # Extract token usage
        usage = response.usage
        if usage:
            model = kwargs.get("model", "unknown")
            cost_tracker.track_chat_completion(
                model=model,
                input_tokens=usage.prompt_tokens or 0,
                output_tokens=usage.completion_tokens or 0,
                duration=duration,
                metadata={
                    "messages_count": len(kwargs.get("messages", [])),
                    "temperature": kwargs.get("temperature"),
                }
            )
        
        return response
    
    def tracked_embeddings_create(*args, **kwargs):
        """Tracked embeddings.create."""
        start_time = time.time()
        response = original_embeddings_create(*args, **kwargs)
        duration = time.time() - start_time
        
        # Extract token usage
        usage = response.usage
        if usage:
            model = kwargs.get("model", "unknown")
            input_texts = kwargs.get("input", [])
            batch_size = len(input_texts) if isinstance(input_texts, list) else 1
            
            cost_tracker.track_embedding(
                model=model,
                input_tokens=usage.total_tokens or 0,
                duration=duration,
                batch_size=batch_size,
                metadata={
                    "input_count": batch_size,
                }
            )
        
        return response
    
    # Replace methods
    client.chat.completions.create = tracked_chat_create
    client.embeddings.create = tracked_embeddings_create
    
    # Mark as tracked
    client._tracked = True
    
    return client


def patch_get_openai_client():
    """
    Patch the get_openai_client function in kg.extractor to return a tracked client.
    This is a global patch that affects all clients created via that function.
    """
    import core_engine.kg.extractor as extractor_module
    
    original_get_client = extractor_module.get_openai_client
    
    def tracked_get_client():
        """Get OpenAI client with cost tracking."""
        client = original_get_client()
        return patch_openai_client(client)
    
    extractor_module.get_openai_client = tracked_get_client


def patch_ingest_qdrant_client():
    """
    Patch the OpenAI client creation in ingest_qdrant to use tracked client.
    """
    import core_engine.embeddings.ingest_qdrant as ingest_module
    
    # The ingest_qdrant function creates its own client
    # We need to patch it at the point of creation
    original_ingest = ingest_module.ingest_qdrant
    
    def tracked_ingest(*args, **kwargs):
        """Tracked ingest_qdrant."""
        # Patch the client creation inside the function
        # We'll need to modify the function to accept a client parameter
        # For now, we'll patch it after creation
        return original_ingest(*args, **kwargs)
    
    # This is more complex - we'd need to modify ingest_qdrant itself
    # For now, let's create a wrapper function instead


def enable_cost_tracking():
    """
    Enable cost tracking globally by patching OpenAI client creation.
    Call this before processing to track all API calls.
    """
    patch_get_openai_client()
    # Note: ingest_qdrant creates its own client, so we need to patch it differently
    # We'll handle that in the process_with_metrics script

