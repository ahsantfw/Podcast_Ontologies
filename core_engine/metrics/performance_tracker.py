"""
Performance tracking for ingestion operations.
Tracks time, throughput, and resource usage.
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    items_processed: int = 0
    items_per_second: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, items_processed: int = 0, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Mark operation as finished."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.items_processed = items_processed
        if self.duration > 0:
            self.items_per_second = items_processed / self.duration
        if metadata:
            self.metadata.update(metadata)


@dataclass
class PerformanceSummary:
    """Summary of performance metrics."""
    total_operations: int = 0
    total_duration: float = 0.0
    total_items_processed: int = 0
    overall_throughput: Optional[float] = None
    by_operation: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    operations: List[OperationMetrics] = field(default_factory=list)


class PerformanceTracker:
    """Track performance metrics for ingestion operations."""
    
    def __init__(self, save_path: Optional[Path] = None):
        """
        Initialize performance tracker.
        
        Args:
            save_path: Optional path to save metrics (JSON)
        """
        self.save_path = save_path
        self.operations: List[OperationMetrics] = []
        self.active_operations: Dict[str, OperationMetrics] = {}
        
    def start_operation(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start tracking an operation.
        
        Args:
            name: Operation name (e.g., "load_transcripts", "extract_kg")
            metadata: Optional metadata
            
        Returns:
            Operation ID (for nested operations)
        """
        op_id = f"{name}_{len(self.operations)}"
        operation = OperationMetrics(
            name=name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.active_operations[op_id] = operation
        return op_id
    
    def finish_operation(
        self,
        op_id: str,
        items_processed: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OperationMetrics:
        """
        Finish tracking an operation.
        
        Args:
            op_id: Operation ID from start_operation
            items_processed: Number of items processed
            metadata: Optional additional metadata
            
        Returns:
            Completed OperationMetrics
        """
        if op_id not in self.active_operations:
            raise ValueError(f"Operation {op_id} not found")
        
        operation = self.active_operations.pop(op_id)
        operation.finish(items_processed, metadata)
        self.operations.append(operation)
        return operation
    
    def get_summary(self) -> PerformanceSummary:
        """Get summary of all tracked operations."""
        if not self.operations:
            return PerformanceSummary()
        
        total_duration = sum(op.duration or 0 for op in self.operations)
        total_items = sum(op.items_processed for op in self.operations)
        overall_throughput = total_items / total_duration if total_duration > 0 else None
        
        # Group by operation name
        by_operation = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0.0,
            "total_items": 0,
            "avg_duration": 0.0,
            "avg_throughput": 0.0,
            "min_duration": float("inf"),
            "max_duration": 0.0
        })
        
        for op in self.operations:
            if op.duration is None:
                continue
                
            stats = by_operation[op.name]
            stats["count"] += 1
            stats["total_duration"] += op.duration
            stats["total_items"] += op.items_processed
            stats["min_duration"] = min(stats["min_duration"], op.duration)
            stats["max_duration"] = max(stats["max_duration"], op.duration)
        
        # Calculate averages
        for stats in by_operation.values():
            if stats["count"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["count"]
                if stats["total_duration"] > 0:
                    stats["avg_throughput"] = stats["total_items"] / stats["total_duration"]
            if stats["min_duration"] == float("inf"):
                stats["min_duration"] = 0.0
        
        return PerformanceSummary(
            total_operations=len(self.operations),
            total_duration=total_duration,
            total_items_processed=total_items,
            overall_throughput=overall_throughput,
            by_operation=dict(by_operation),
            operations=self.operations.copy()
        )
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save performance data to JSON file."""
        save_to = path or self.save_path
        if not save_to:
            return
        
        save_to.parent.mkdir(parents=True, exist_ok=True)
        
        summary = self.get_summary()
        data = {
            "summary": {
                "total_operations": summary.total_operations,
                "total_duration": summary.total_duration,
                "total_items_processed": summary.total_items_processed,
                "overall_throughput": summary.overall_throughput,
                "by_operation": summary.by_operation,
            },
            "operations": [
                {
                    "name": op.name,
                    "duration": op.duration,
                    "items_processed": op.items_processed,
                    "items_per_second": op.items_per_second,
                    "metadata": op.metadata
                }
                for op in self.operations
            ]
        }
        
        with open(save_to, "w") as f:
            json.dump(data, f, indent=2)
    
    def reset(self) -> None:
        """Reset all tracked data."""
        self.operations.clear()
        self.active_operations.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save if path provided."""
        if self.save_path:
            self.save()


# Global tracker instance
_global_tracker: Optional[PerformanceTracker] = None


def get_performance_tracker(save_path: Optional[Path] = None) -> PerformanceTracker:
    """Get or create global performance tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = PerformanceTracker(save_path=save_path)
    return _global_tracker


def reset_performance_tracker() -> None:
    """Reset global performance tracker."""
    global _global_tracker
    if _global_tracker:
        _global_tracker.reset()

