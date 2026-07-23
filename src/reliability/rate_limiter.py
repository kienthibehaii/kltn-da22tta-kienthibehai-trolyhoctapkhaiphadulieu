# reliability/rate_limiter.py - Advanced Rate Limiting & Circuit Breaker
"""
Production-ready rate limiting với:
- Token bucket algorithm
- Sliding window
- Circuit breaker pattern
- Quota monitoring
"""

import time
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens
            refill_rate: Tokens per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
    
    def available_tokens(self) -> int:
        """Get available tokens"""
        self._refill()
        return int(self.tokens)


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for precise control"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
    
    def allow_request(self) -> bool:
        """Check if request is allowed"""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Remove old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request"""
        if len(self.requests) < self.max_requests:
            return 0.0
        
        oldest = self.requests[0]
        wait_until = oldest + self.window_seconds
        return max(0, wait_until - time.time())


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: HALF_OPEN, attempting recovery")
            else:
                raise Exception(f"Circuit breaker OPEN. Wait {self._time_until_retry()}s")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: HALF_OPEN, attempting recovery")
            else:
                raise Exception(f"Circuit breaker OPEN. Wait {self._time_until_retry()}s")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker: CLOSED, recovered")
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker: OPEN after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt recovery"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _time_until_retry(self) -> float:
        """Time until retry is allowed"""
        if not self.last_failure_time:
            return 0
        elapsed = time.time() - self.last_failure_time
        return max(0, self.recovery_timeout - elapsed)


class APIRateLimiter:
    """Comprehensive API rate limiter with multiple strategies"""
    
    def __init__(self):
        # Gemini API limits (free tier)
        self.limiters = {
            "gemini_flash": {
                "per_minute": SlidingWindowRateLimiter(15, 60),
                "per_day": SlidingWindowRateLimiter(1500, 86400),
                "circuit_breaker": CircuitBreaker(failure_threshold=3, recovery_timeout=60)
            },
            "gemini_pro": {
                "per_minute": SlidingWindowRateLimiter(2, 60),
                "per_day": SlidingWindowRateLimiter(50, 86400),
                "circuit_breaker": CircuitBreaker(failure_threshold=3, recovery_timeout=120)
            },
            "translation": {
                "per_minute": SlidingWindowRateLimiter(10, 60),
                "circuit_breaker": CircuitBreaker(failure_threshold=5, recovery_timeout=30)
            }
        }
        
        # Token buckets for burst control
        self.token_buckets = {
            "gemini_flash": TokenBucket(capacity=10, refill_rate=0.25),  # 15/min
            "translation": TokenBucket(capacity=5, refill_rate=0.17)     # 10/min
        }
    
    def check_rate_limit(self, service: str) -> tuple[bool, float]:
        """
        Check if request is allowed
        
        Returns:
            (allowed, wait_time)
        """
        if service not in self.limiters:
            return True, 0.0
        
        limiter_config = self.limiters[service]
        
        # Check all rate limiters
        for name, limiter in limiter_config.items():
            if name == "circuit_breaker":
                continue
            
            if not limiter.allow_request():
                wait_time = limiter.get_wait_time()
                logger.warning(f"Rate limit hit for {service}/{name}. Wait {wait_time:.1f}s")
                return False, wait_time
        
        # Check token bucket
        if service in self.token_buckets:
            if not self.token_buckets[service].consume():
                logger.warning(f"Token bucket exhausted for {service}")
                return False, 1.0
        
        return True, 0.0
    
    def get_circuit_breaker(self, service: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker for service"""
        if service in self.limiters:
            return self.limiters[service].get("circuit_breaker")
        return None
    
    def get_status(self) -> Dict:
        """Get rate limiter status"""
        status = {}
        
        for service, config in self.limiters.items():
            service_status = {}
            
            for name, limiter in config.items():
                if name == "circuit_breaker":
                    service_status["circuit_state"] = limiter.state.value
                    service_status["failure_count"] = limiter.failure_count
                elif isinstance(limiter, SlidingWindowRateLimiter):
                    service_status[name] = {
                        "used": len(limiter.requests),
                        "limit": limiter.max_requests,
                        "wait_time": limiter.get_wait_time()
                    }
            
            if service in self.token_buckets:
                bucket = self.token_buckets[service]
                service_status["tokens_available"] = bucket.available_tokens()
            
            status[service] = service_status
        
        return status


# Global rate limiter instance
rate_limiter = APIRateLimiter()


def with_rate_limit(service: str):
    """Decorator for rate limiting"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Check rate limit
            allowed, wait_time = rate_limiter.check_rate_limit(service)
            
            if not allowed:
                if wait_time > 0:
                    logger.info(f"Rate limited, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"Rate limit exceeded for {service}")
            
            # Execute with circuit breaker
            circuit_breaker = rate_limiter.get_circuit_breaker(service)
            if circuit_breaker:
                return await circuit_breaker.call_async(func, *args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # Check rate limit
            allowed, wait_time = rate_limiter.check_rate_limit(service)
            
            if not allowed:
                if wait_time > 0:
                    logger.info(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Rate limit exceeded for {service}")
            
            # Execute with circuit breaker
            circuit_breaker = rate_limiter.get_circuit_breaker(service)
            if circuit_breaker:
                return circuit_breaker.call(func, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
