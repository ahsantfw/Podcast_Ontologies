"""
OpenAI client wrapper with cost tracking.
Wraps OpenAI API calls to automatically track token usage and costs.
"""

from __future__ import annotations

import time
from typing import Optional, List, Dict, Any
from openai import OpenAI

from core_engine.metrics.cost_tracker import get_cost_tracker


class TrackedOpenAIClient:
    """OpenAI client wrapper with automatic cost tracking."""
    
    def __init__(self, client: OpenAI):
        """
        Initialize tracked client.
        
        Args:
            client: OpenAI client instance
        """
        self.client = client
        self.cost_tracker = get_cost_tracker()
    
    def chat_completions_create(self, *args, **kwargs) -> Any:
        """
        Tracked chat.completions.create call.
        
        Returns:
            ChatCompletion response
        """
        start_time = time.time()
        response = self.client.chat.completions.create(*args, **kwargs)
        duration = time.time() - start_time
        
        # Extract token usage
        usage = response.usage
        if usage:
            model = kwargs.get("model", "unknown")
            self.cost_tracker.track_chat_completion(
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
    
    def embeddings_create(self, *args, **kwargs) -> Any:
        """
        Tracked embeddings.create call.
        
        Returns:
            Embedding response
        """
        start_time = time.time()
        response = self.client.embeddings.create(*args, **kwargs)
        duration = time.time() - start_time
        
        # Extract token usage
        usage = response.usage
        if usage:
            model = kwargs.get("model", "unknown")
            input_texts = kwargs.get("input", [])
            batch_size = len(input_texts) if isinstance(input_texts, list) else 1
            
            self.cost_tracker.track_embedding(
                model=model,
                input_tokens=usage.total_tokens or 0,
                duration=duration,
                batch_size=batch_size,
                metadata={
                    "input_count": batch_size,
                }
            )
        
        return response
    
    def __getattr__(self, name):
        """Delegate other attributes to underlying client."""
        return getattr(self.client, name)


def wrap_openai_client(client: OpenAI) -> TrackedOpenAIClient:
    """
    Wrap OpenAI client with cost tracking.
    
    Args:
        client: OpenAI client instance
        
    Returns:
        TrackedOpenAIClient wrapper
    """
    return TrackedOpenAIClient(client)

