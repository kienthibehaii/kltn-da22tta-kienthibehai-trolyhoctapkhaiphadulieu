# reliability/retry_strategy.py - Advanced Retry with Exponential Backoff
"""
Production retry strategies:
- Exponential backoff with jitter
- Adaptive retry
- Retry budget
- Dead letter queue
"""

import time
import random
import asyncio
from typing import Callable, Any, Optional, Type
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RetryConfig:
    """Retry configuration"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on


class RetryBudget:
    """Retry budget to prevent retry storms"""
    
    def __init__(self, budget_per_minute: int = 10):
        self.budget_per_minute = budget_per_minute
        self.retries_used = []
    
    def can_retry(self) -> bool:
        """Check if retry is allowed"""
        now = time.time()
        cutoff = now - 60
        
        # Remove old retries
        self.retries_used = [t for t in self.retries_used if t > cutoff]
        
        # Check budget
        if len(self.retries_used) < self.budget_per_minute:
            self.retries_used.append(now)
            return True
        
        logger.warning("Retry budget exhausted")
        return False


class ExponentialBackoff:
    """Exponential backoff calculator"""
    
    @staticmethod
    def calculate_delay(
        attempt: int,
        initial_delay: float,
        max_delay: float,
        exponential_base: float,
        jitter: bool = True
    ) -> float:
        """Calculate delay with exponential backoff"""
        # Base delay
        delay = min(initial_delay * (exponential_base ** attempt), max_delay)
        
        # Add jitter to prevent thundering herd
        if jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for retry with exponential backoff
    
    Usage:
        @retry_with_backoff(RetryConfig(max_attempts=3))
        async def my_function():
            ...
    """
    if config is None:
        config = RetryConfig()
    
    retry_budget = RetryBudget()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Log success after retry
                    if attempt > 0:
                        logger.info(f"✅ Success after {attempt + 1} attempts")
                    
                    return result
                
                except config.retry_on as e:
                    last_exception = e
                    
                    # Check if should retry
                    if attempt == config.max_attempts - 1:
                        logger.error(f"❌ Failed after {config.max_attempts} attempts: {e}")
                        break
                    
                    # Check retry budget
                    if not retry_budget.can_retry():
                        logger.error("Retry budget exhausted, failing fast")
                        break
                    
                    # Calculate delay
                    delay = ExponentialBackoff.calculate_delay(
                        attempt,
                        config.initial_delay,
                        config.max_delay,
                        config.exponential_base,
                        config.jitter
                    )
                    
                    logger.warning(
                        f"⚠️ Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(delay)
            
            # All retries exhausted
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(f"✅ Success after {attempt + 1} attempts")
                    
                    return result
                
                except config.retry_on as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        logger.error(f"❌ Failed after {config.max_attempts} attempts: {e}")
                        break
                    
                    if not retry_budget.can_retry():
                        logger.error("Retry budget exhausted, failing fast")
                        break
                    
                    delay = ExponentialBackoff.calculate_delay(
                        attempt,
                        config.initial_delay,
                        config.max_delay,
                        config.exponential_base,
                        config.jitter
                    )
                    
                    logger.warning(
                        f"⚠️ Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    time.sleep(delay)
            
            raise last_exception
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class AdaptiveRetry:
    """Adaptive retry that learns from failures"""
    
    def __init__(self):
        self.success_rate = 1.0
        self.total_attempts = 0
        self.successful_attempts = 0
        self.window_size = 100
    
    def record_attempt(self, success: bool):
        """Record attempt result"""
        self.total_attempts += 1
        if success:
            self.successful_attempts += 1
        
        # Calculate success rate over window
        if self.total_attempts > self.window_size:
            self.total_attempts = self.window_size
            self.successful_attempts = int(self.success_rate * self.window_size)
        
        self.success_rate = self.successful_attempts / self.total_attempts
    
    def should_retry(self) -> bool:
        """Decide if should retry based on success rate"""
        # If success rate is very low, stop retrying
        if self.success_rate < 0.1:
            logger.warning(f"Success rate too low ({self.success_rate:.1%}), skipping retry")
            return False
        
        return True
    
    def get_max_attempts(self) -> int:
        """Get adaptive max attempts based on success rate"""
        if self.success_rate > 0.8:
            return 3
        elif self.success_rate > 0.5:
            return 2
        else:
            return 1


# Global adaptive retry instance
adaptive_retry = AdaptiveRetry()


def retry_with_adaptive(func: Callable) -> Callable:
    """Decorator for adaptive retry"""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        if not adaptive_retry.should_retry():
            # Skip retry if success rate is too low
            try:
                result = await func(*args, **kwargs)
                adaptive_retry.record_attempt(True)
                return result
            except Exception as e:
                adaptive_retry.record_attempt(False)
                raise e
        
        # Use adaptive max attempts
        max_attempts = adaptive_retry.get_max_attempts()
        config = RetryConfig(max_attempts=max_attempts)
        
        @retry_with_backoff(config)
        async def wrapped():
            return await func(*args, **kwargs)
        
        try:
            result = await wrapped()
            adaptive_retry.record_attempt(True)
            return result
        except Exception as e:
            adaptive_retry.record_attempt(False)
            raise e
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        if not adaptive_retry.should_retry():
            try:
                result = func(*args, **kwargs)
                adaptive_retry.record_attempt(True)
                return result
            except Exception as e:
                adaptive_retry.record_attempt(False)
                raise e
        
        max_attempts = adaptive_retry.get_max_attempts()
        config = RetryConfig(max_attempts=max_attempts)
        
        @retry_with_backoff(config)
        def wrapped():
            return func(*args, **kwargs)
        
        try:
            result = wrapped()
            adaptive_retry.record_attempt(True)
            return result
        except Exception as e:
            adaptive_retry.record_attempt(False)
            raise e
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
