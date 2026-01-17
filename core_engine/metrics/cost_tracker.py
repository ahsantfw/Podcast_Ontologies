"""
Cost tracking for OpenAI API calls.
Tracks token usage and calculates costs based on model pricing.
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path


# OpenAI pricing per 1M tokens (as of 2024)
PRICING = {
    # Chat models
    "gpt-4o": {"input": 2.50, "output": 10.00},  # $2.50/$10 per 1M tokens
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    
    # Embedding models
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},  # $0.13 per 1M tokens
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
}


@dataclass
class APICall:
    """Single API call record."""
    timestamp: float
    model: str
    operation: str  # "chat", "embedding"
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    duration: float = 0.0  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostSummary:
    """Summary of costs and usage."""
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_duration: float = 0.0
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_operation: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    calls: List[APICall] = field(default_factory=list)


class CostTracker:
    """Track OpenAI API costs and token usage."""
    
    def __init__(self, save_path: Optional[Path] = None):
        """
        Initialize cost tracker.
        
        Args:
            save_path: Optional path to save cost data (JSON)
        """
        self.save_path = save_path
        self.calls: List[APICall] = []
        self._lock = False  # Simple lock for thread safety
        
    def track_chat_completion(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APICall:
        """
        Track a chat completion API call.
        
        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            duration: Call duration in seconds
            metadata: Optional metadata
            
        Returns:
            APICall record
        """
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        call = APICall(
            timestamp=time.time(),
            model=model,
            operation="chat",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            duration=duration,
            metadata=metadata or {}
        )
        self.calls.append(call)
        return call
    
    def track_embedding(
        self,
        model: str,
        input_tokens: int,
        duration: float,
        batch_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APICall:
        """
        Track an embedding API call.
        
        Args:
            model: Model name
            input_tokens: Input token count (total across batch)
            duration: Call duration in seconds
            batch_size: Optional batch size
            metadata: Optional metadata
            
        Returns:
            APICall record
        """
        cost = self._calculate_cost(model, input_tokens, 0)
        call = APICall(
            timestamp=time.time(),
            model=model,
            operation="embedding",
            input_tokens=input_tokens,
            output_tokens=0,
            cost=cost,
            duration=duration,
            metadata={
                **(metadata or {}),
                "batch_size": batch_size
            }
        )
        self.calls.append(call)
        return call
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for API call."""
        if model not in PRICING:
            # Default to gpt-4o pricing if unknown
            pricing = PRICING["gpt-4o"]
        else:
            pricing = PRICING[model]
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    def get_summary(self) -> CostSummary:
        """Get summary of all tracked calls."""
        if not self.calls:
            return CostSummary()
        
        total_input = sum(c.input_tokens for c in self.calls)
        total_output = sum(c.output_tokens for c in self.calls)
        total_cost = sum(c.cost for c in self.calls)
        total_duration = sum(c.duration for c in self.calls)
        
        # Group by model
        by_model = defaultdict(lambda: {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "duration": 0.0
        })
        
        for call in self.calls:
            by_model[call.model]["calls"] += 1
            by_model[call.model]["input_tokens"] += call.input_tokens
            by_model[call.model]["output_tokens"] += call.output_tokens
            by_model[call.model]["cost"] += call.cost
            by_model[call.model]["duration"] += call.duration
        
        # Group by operation
        by_operation = defaultdict(lambda: {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "duration": 0.0
        })
        
        for call in self.calls:
            by_operation[call.operation]["calls"] += 1
            by_operation[call.operation]["input_tokens"] += call.input_tokens
            by_operation[call.operation]["output_tokens"] += call.output_tokens
            by_operation[call.operation]["cost"] += call.cost
            by_operation[call.operation]["duration"] += call.duration
        
        return CostSummary(
            total_calls=len(self.calls),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost=total_cost,
            total_duration=total_duration,
            by_model=dict(by_model),
            by_operation=dict(by_operation),
            calls=self.calls.copy()
        )
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save cost data to JSON file."""
        save_to = path or self.save_path
        if not save_to:
            return
        
        save_to.parent.mkdir(parents=True, exist_ok=True)
        
        summary = self.get_summary()
        data = {
            "summary": {
                "total_calls": summary.total_calls,
                "total_input_tokens": summary.total_input_tokens,
                "total_output_tokens": summary.total_output_tokens,
                "total_cost": summary.total_cost,
                "total_duration": summary.total_duration,
                "by_model": summary.by_model,
                "by_operation": summary.by_operation,
            },
            "calls": [
                {
                    "timestamp": c.timestamp,
                    "model": c.model,
                    "operation": c.operation,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "cost": c.cost,
                    "duration": c.duration,
                    "metadata": c.metadata
                }
                for c in self.calls
            ]
        }
        
        with open(save_to, "w") as f:
            json.dump(data, f, indent=2)
    
    def reset(self) -> None:
        """Reset all tracked data."""
        self.calls.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save if path provided."""
        if self.save_path:
            self.save()


# Global tracker instance
_global_tracker: Optional[CostTracker] = None


def get_cost_tracker(save_path: Optional[Path] = None) -> CostTracker:
    """Get or create global cost tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker(save_path=save_path)
    return _global_tracker


def reset_cost_tracker() -> None:
    """Reset global cost tracker."""
    global _global_tracker
    if _global_tracker:
        _global_tracker.reset()

