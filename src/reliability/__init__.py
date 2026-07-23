# reliability/__init__.py - Reliability Engineering Package
"""
Production reliability components for RAG system
"""

from .rate_limiter import (
    rate_limiter,
    with_rate_limit,
    CircuitBreaker,
    APIRateLimiter
)

from .retry_strategy import (
    retry_with_backoff,
    retry_with_adaptive,
    RetryConfig,
    adaptive_retry
)

from .cache_manager import (
    init_cache,
    cached,
    cache_manager,
    TranslationCache,
    EmbeddingCache,
    ResponseCache
)

from .api_key_manager import (
    init_api_keys,
    get_api_key,
    get_model_and_key,
    api_key_manager,
    fallback_manager
)

from .graceful_degradation import (
    degradation_manager,
    with_graceful_degradation,
    FallbackResponse,
    TimeoutHandler,
    ServiceMode
)

__all__ = [
    # Rate limiting
    "rate_limiter",
    "with_rate_limit",
    "CircuitBreaker",
    "APIRateLimiter",
    
    # Retry
    "retry_with_backoff",
    "retry_with_adaptive",
    "RetryConfig",
    "adaptive_retry",
    
    # Cache
    "init_cache",
    "cached",
    "cache_manager",
    "TranslationCache",
    "EmbeddingCache",
    "ResponseCache",
    
    # API keys
    "init_api_keys",
    "get_api_key",
    "get_model_and_key",
    "api_key_manager",
    "fallback_manager",
    
    # Degradation
    "degradation_manager",
    "with_graceful_degradation",
    "FallbackResponse",
    "TimeoutHandler",
    "ServiceMode"
]
