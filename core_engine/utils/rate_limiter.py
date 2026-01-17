"""
Rate limiting and retry utilities for OpenAI API calls.
Handles rate limits, quota limits, and other API errors with exponential backoff.
"""

from __future__ import annotations

import time
import random
import threading
from typing import Optional, Callable, Any, TypeVar
from functools import wraps
import logging

try:
    from openai import (
        RateLimitError,
        APIError,
        APIConnectionError,
        APITimeoutError,
        APIStatusError,
    )
    OPENAI_ERRORS = (
        RateLimitError,
        APIError,
        APIConnectionError,
        APITimeoutError,
        APIStatusError,
    )
except ImportError:
    # Fallback if openai not installed
    OPENAI_ERRORS = Exception

T = TypeVar('T')

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with exponential backoff for OpenAI API calls."""
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        respect_rate_limits: bool = True,
        requests_per_minute: Optional[int] = None,
        tokens_per_minute: Optional[int] = None,
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
            respect_rate_limits: Whether to respect rate limits between calls
            requests_per_minute: Optional RPM limit (e.g., 500 for GPT-4o)
            tokens_per_minute: Optional TPM limit (e.g., 1,000,000 for GPT-4o)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.respect_rate_limits = respect_rate_limits
        
        # Rate limiting
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.request_times = []
        self.token_usage = []
        self._lock = threading.Lock()  # Thread-safe lock for async compatibility
        
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter (0-25% of delay)
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount
        
        return delay
    
    def _wait_for_rate_limit(self):
        """Wait if we're approaching rate limits (thread-safe)."""
        if not self.respect_rate_limits:
            return
        
        with self._lock:
            now = time.time()
            
            # Clean old entries (older than 1 minute)
            self.request_times = [t for t in self.request_times if now - t < 60]
            self.token_usage = [(t, tokens) for t, tokens in self.token_usage if now - t < 60]
        
            # Check requests per minute
            if self.requests_per_minute:
                if len(self.request_times) >= self.requests_per_minute:
                    # Wait until oldest request is 1 minute old
                    oldest = min(self.request_times) if self.request_times else now
                    wait_time = 60 - (now - oldest) + 0.1  # Small buffer
                    if wait_time > 0:
                        logger.info(f"Rate limit: Waiting {wait_time:.1f}s (RPM limit: {self.requests_per_minute})")
                        time.sleep(wait_time)
            
            # Check tokens per minute (simplified - we don't know tokens until after call)
            # This is a conservative estimate
            if self.tokens_per_minute:
                recent_tokens = sum(tokens for _, tokens in self.token_usage)
                if recent_tokens >= self.tokens_per_minute * 0.9:  # 90% threshold
                    # Wait a bit
                    wait_time = 2.0
                    logger.info(f"Rate limit: Waiting {wait_time:.1f}s (TPM threshold: {self.tokens_per_minute * 0.9})")
                    time.sleep(wait_time)
    
    def _record_request(self, tokens: int = 0):
        """Record a request for rate limiting (thread-safe)."""
        with self._lock:
            now = time.time()
            self.request_times.append(now)
            if tokens > 0:
                self.token_usage.append((now, tokens))
    
    def retry_with_backoff(
        self,
        func: Callable[[], T],
        operation_name: str = "API call",
        on_retry: Optional[Callable[[int, Exception], None]] = None,
    ) -> T:
        """
        Execute function with retry and exponential backoff.
        
        Args:
            func: Function to execute
            operation_name: Name of operation for logging
            on_retry: Optional callback on retry (attempt, error)
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Wait for rate limits before making request
                self._wait_for_rate_limit()
                
                # Execute function
                result = func()
                
                # Record successful request (estimate tokens if possible)
                # We'll update this after getting actual token usage
                self._record_request()
                
                return result
                
            except OPENAI_ERRORS as e:
                last_exception = e
                
                # Check if it's a rate limit error
                is_rate_limit = (
                    isinstance(e, RateLimitError) or
                    (hasattr(e, 'status_code') and e.status_code == 429) or
                    "rate limit" in str(e).lower() or
                    "quota" in str(e).lower()
                )
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    
                    if is_rate_limit:
                        # For rate limits, use longer delay
                        delay = max(delay, 60.0)  # At least 60 seconds for rate limits
                        logger.warning(
                            f"Rate limit hit for {operation_name}. "
                            f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                    else:
                        logger.warning(
                            f"Error in {operation_name}: {e}. "
                            f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                    
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    time.sleep(delay)
                else:
                    logger.error(f"Failed {operation_name} after {self.max_retries} retries: {e}")
                    raise
        
        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Failed {operation_name} for unknown reason")
    
    def __call__(self, func: Callable[[], T]) -> T:
        """Make rate limiter callable as a decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.retry_with_backoff(
                lambda: func(*args, **kwargs),
                operation_name=func.__name__
            )
        return wrapper


# Default rate limiter instance
_default_limiter = RateLimiter(
    max_retries=5,
    initial_delay=1.0,
    max_delay=120.0,  # 2 minutes max
    requests_per_minute=500,  # Conservative for GPT-4o
    tokens_per_minute=1_000_000,  # Conservative for GPT-4o
)


def with_retry(
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 120.0,
    operation_name: Optional[str] = None,
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Usage:
        @with_retry(max_retries=5, operation_name="extract_kg")
        def extract_kg(chunks):
            # Your code
            return result
    """
    limiter = RateLimiter(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
    )
    
    def decorator(func: Callable[[], T]) -> Callable[[], T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return limiter.retry_with_backoff(
                lambda: func(*args, **kwargs),
                operation_name=name
            )
        return wrapper
    
    return decorator


def get_rate_limiter(
    requests_per_minute: Optional[int] = None,
    tokens_per_minute: Optional[int] = None,
) -> RateLimiter:
    """
    Get a rate limiter with custom limits.
    
    Args:
        requests_per_minute: RPM limit (default: 500)
        tokens_per_minute: TPM limit (default: 1,000,000)
        
    Returns:
        RateLimiter instance
    """
    return RateLimiter(
        requests_per_minute=requests_per_minute or 500,
        tokens_per_minute=tokens_per_minute or 1_000_000,
    )

