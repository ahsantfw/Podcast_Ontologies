"""
Reasoner Pool - Singleton pattern for reusing KGReasoner instances

This module provides a connection pool to avoid creating new reasoner instances
for every request, which significantly improves performance.
"""

import threading
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from core_engine.reasoning import create_reasoner
from core_engine.reasoning.reasoning import KGReasoner
from core_engine.logging import get_logger

logger = get_logger("backend.app.core.reasoner_pool")


class ReasonerPool:
    """
    Singleton pool for managing KGReasoner instances per workspace.
    
    Features:
    - One reasoner per workspace (reused across requests)
    - Thread-safe access
    - Automatic cleanup of idle reasoners
    - Graceful error handling
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - only one pool instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ReasonerPool, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the pool."""
        if self._initialized:
            return
        
        self._lock = threading.Lock()
        self._reasoners: Dict[str, KGReasoner] = {}
        self._last_used: Dict[str, datetime] = {}
        self._access_count: Dict[str, int] = {}
        self._idle_timeout = timedelta(minutes=30)  # Clean up after 30 min idle
        self._max_reasoners = 50  # Maximum reasoners to keep in memory
        self._initialized = True
        
        logger.info("reasoner_pool_initialized")
    
    def get_reasoner(
        self,
        workspace_id: str,
        use_llm: bool = True,
        use_hybrid: bool = True,
    ) -> KGReasoner:
        """
        Get or create a reasoner for the workspace.
        
        Args:
            workspace_id: Workspace identifier
            use_llm: Whether to use LLM
            use_hybrid: Whether to use hybrid retrieval
            
        Returns:
            KGReasoner instance
        """
        with self._lock:
            # Check if reasoner exists and is still valid
            if workspace_id in self._reasoners:
                reasoner = self._reasoners[workspace_id]
                
                # Check if reasoner is still usable (has required components)
                if self._is_reasoner_valid(reasoner, use_llm, use_hybrid):
                    self._last_used[workspace_id] = datetime.now()
                    self._access_count[workspace_id] = self._access_count.get(workspace_id, 0) + 1
                    logger.debug(f"reasoner_reused", extra={
                        "context": {
                            "workspace_id": workspace_id,
                            "access_count": self._access_count[workspace_id]
                        }
                    })
                    return reasoner
                else:
                    # Reasoner is invalid, remove it
                    logger.warning(f"reasoner_invalid_removing", extra={
                        "context": {"workspace_id": workspace_id}
                    })
                    self._remove_reasoner(workspace_id)
            
            # Check if we're at max capacity
            if len(self._reasoners) >= self._max_reasoners:
                self._cleanup_idle_reasoners()
            
            # Create new reasoner
            logger.info(f"reasoner_creating", extra={
                "context": {
                    "workspace_id": workspace_id,
                    "total_reasoners": len(self._reasoners)
                }
            })
            
            try:
                reasoner = create_reasoner(
                    workspace_id=workspace_id,
                    use_llm=use_llm,
                    use_hybrid=use_hybrid,
                )
                
                self._reasoners[workspace_id] = reasoner
                self._last_used[workspace_id] = datetime.now()
                self._access_count[workspace_id] = 1
                
                logger.info(f"reasoner_created", extra={
                    "context": {"workspace_id": workspace_id}
                })
                
                return reasoner
                
            except Exception as e:
                logger.error(f"reasoner_creation_failed", exc_info=True, extra={
                    "context": {"workspace_id": workspace_id, "error": str(e)}
                })
                raise
    
    def _is_reasoner_valid(
        self,
        reasoner: KGReasoner,
        use_llm: bool,
        use_hybrid: bool,
    ) -> bool:
        """
        Check if reasoner is still valid for the requested configuration.
        
        Args:
            reasoner: KGReasoner instance
            use_llm: Whether LLM is required
            use_hybrid: Whether hybrid retrieval is required
            
        Returns:
            True if reasoner is valid, False otherwise
        """
        try:
            # Check if reasoner has required components
            if use_hybrid and not reasoner.hybrid_retriever:
                return False
            if use_llm and not reasoner.use_llm:
                return False
            
            # Check if components are still functional
            if reasoner.neo4j_client:
                # Quick health check - try a simple query
                try:
                    reasoner.neo4j_client.execute_read(
                        "RETURN 1 as test",
                        {}
                    )
                except Exception:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _remove_reasoner(self, workspace_id: str) -> None:
        """Remove a reasoner from the pool."""
        if workspace_id in self._reasoners:
            try:
                reasoner = self._reasoners[workspace_id]
                reasoner.close()
            except Exception as e:
                logger.warning(f"reasoner_cleanup_failed", extra={
                    "context": {"workspace_id": workspace_id, "error": str(e)}
                })
            
            del self._reasoners[workspace_id]
            if workspace_id in self._last_used:
                del self._last_used[workspace_id]
            if workspace_id in self._access_count:
                del self._access_count[workspace_id]
    
    def _cleanup_idle_reasoners(self) -> None:
        """Clean up reasoners that haven't been used recently."""
        now = datetime.now()
        idle_workspaces = []
        
        for workspace_id, last_used in self._last_used.items():
            if now - last_used > self._idle_timeout:
                idle_workspaces.append(workspace_id)
        
        # Remove oldest idle reasoners first
        idle_workspaces.sort(key=lambda w: self._last_used.get(w, datetime.min))
        
        # Remove up to half of idle reasoners
        remove_count = min(len(idle_workspaces), len(self._reasoners) // 2)
        for workspace_id in idle_workspaces[:remove_count]:
            logger.info(f"reasoner_cleanup_idle", extra={
                "context": {"workspace_id": workspace_id}
            })
            self._remove_reasoner(workspace_id)
    
    def cleanup_all(self) -> None:
        """Clean up all reasoners (for shutdown)."""
        with self._lock:
            workspace_ids = list(self._reasoners.keys())
            for workspace_id in workspace_ids:
                self._remove_reasoner(workspace_id)
            logger.info(f"reasoner_pool_cleaned_up", extra={
                "context": {"removed_count": len(workspace_ids)}
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "total_reasoners": len(self._reasoners),
                "workspaces": list(self._reasoners.keys()),
                "access_counts": dict(self._access_count),
                "last_used": {
                    w: t.isoformat() 
                    for w, t in self._last_used.items()
                }
            }


# Global singleton instance
_pool_instance: Optional[ReasonerPool] = None
_pool_lock = threading.Lock()


def get_reasoner_pool() -> ReasonerPool:
    """Get the global reasoner pool instance."""
    global _pool_instance
    if _pool_instance is None:
        with _pool_lock:
            if _pool_instance is None:
                _pool_instance = ReasonerPool()
    return _pool_instance
