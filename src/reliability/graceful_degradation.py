# reliability/graceful_degradation.py - Graceful Degradation Strategies
"""
Graceful degradation for production:
- Fallback responses
- Partial results
- Degraded mode
- Service health tracking
"""

import asyncio
from typing import Optional, Any, Callable, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ServiceMode(Enum):
    """Service operation modes"""
    FULL = "full"              # All features available
    DEGRADED = "degraded"      # Limited features
    MINIMAL = "minimal"        # Basic features only
    OFFLINE = "offline"        # Service unavailable


class ServiceHealth:
    """Track service health"""
    
    def __init__(self, name: str):
        self.name = name
        self.mode = ServiceMode.FULL
        self.error_count = 0
        self.success_count = 0
        self.last_error = None
        self.last_success = None
    
    def record_success(self):
        """Record successful operation"""
        self.success_count += 1
        self.last_success = asyncio.get_event_loop().time()
        
        # Recover to better mode
        if self.mode == ServiceMode.DEGRADED and self.success_count > 10:
            self.mode = ServiceMode.FULL
            logger.info(f"{self.name}: Recovered to FULL mode")
    
    def record_error(self, error: Exception):
        """Record error"""
        self.error_count += 1
        self.last_error = str(error)
        
        # Degrade mode based on errors
        if self.error_count > 10:
            self.mode = ServiceMode.OFFLINE
            logger.error(f"{self.name}: Degraded to OFFLINE mode")
        elif self.error_count > 5:
            self.mode = ServiceMode.MINIMAL
            logger.warning(f"{self.name}: Degraded to MINIMAL mode")
        elif self.error_count > 3:
            self.mode = ServiceMode.DEGRADED
            logger.warning(f"{self.name}: Degraded to DEGRADED mode")
    
    def get_status(self) -> Dict:
        """Get health status"""
        return {
            "name": self.name,
            "mode": self.mode.value,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "last_error": self.last_error
        }


class GracefulDegradation:
    """Manage graceful degradation"""
    
    def __init__(self):
        self.services = {}
    
    def register_service(self, name: str) -> ServiceHealth:
        """Register a service"""
        if name not in self.services:
            self.services[name] = ServiceHealth(name)
        return self.services[name]
    
    def get_service(self, name: str) -> Optional[ServiceHealth]:
        """Get service health"""
        return self.services.get(name)
    
    def get_all_status(self) -> Dict:
        """Get status of all services"""
        return {
            name: service.get_status()
            for name, service in self.services.items()
        }


# Global degradation manager
degradation_manager = GracefulDegradation()


class FallbackResponse:
    """Fallback response strategies"""
    
    @staticmethod
    def simple_answer(question: str) -> Dict:
        """Simple fallback answer"""
        return {
            "answer": "Xin lỗi, hệ thống đang gặp sự cố tạm thời. Vui lòng thử lại sau.",
            "sources": [],
            "citations": [],
            "mode": "fallback",
            "confidence": 0.0
        }
    
    @staticmethod
    def cached_answer(question: str, cache) -> Optional[Dict]:
        """Try to get cached answer"""
        # Try to find similar cached question
        # This is a simplified version
        return None
    
    @staticmethod
    def partial_answer(question: str, partial_data: Any) -> Dict:
        """Create partial answer from available data"""
        return {
            "answer": f"Đây là câu trả lời một phần cho: {question}. "
                     "Hệ thống đang trong chế độ giới hạn.",
            "sources": partial_data.get("sources", []) if isinstance(partial_data, dict) else [],
            "citations": [],
            "mode": "partial",
            "confidence": 0.5
        }
    
    @staticmethod
    def search_only_answer(question: str, documents: list) -> Dict:
        """Answer with search results only (no LLM)"""
        if not documents:
            return FallbackResponse.simple_answer(question)
        
        # Create answer from document snippets
        snippets = []
        for i, doc in enumerate(documents[:3], 1):
            content = doc.page_content[:200] if hasattr(doc, 'page_content') else str(doc)[:200]
            snippets.append(f"{i}. {content}...")
        
        answer = "Dựa trên tài liệu tìm được:\n\n" + "\n\n".join(snippets)
        
        return {
            "answer": answer,
            "sources": documents,
            "citations": [],
            "mode": "search_only",
            "confidence": 0.6
        }


async def with_graceful_degradation(
    service_name: str,
    primary_func: Callable,
    fallback_func: Optional[Callable] = None,
    *args,
    **kwargs
) -> Any:
    """
    Execute function with graceful degradation
    
    Args:
        service_name: Name of service
        primary_func: Primary function to execute
        fallback_func: Fallback function if primary fails
        *args, **kwargs: Arguments for functions
    
    Returns:
        Result from primary or fallback function
    """
    # Get or register service
    service = degradation_manager.register_service(service_name)
    
    # Check if service is offline
    if service.mode == ServiceMode.OFFLINE:
        logger.warning(f"{service_name} is OFFLINE, using fallback immediately")
        if fallback_func:
            return await fallback_func(*args, **kwargs)
        else:
            raise Exception(f"Service {service_name} is offline and no fallback available")
    
    # Try primary function
    try:
        result = await primary_func(*args, **kwargs)
        service.record_success()
        return result
    
    except Exception as e:
        logger.error(f"{service_name} failed: {e}")
        service.record_error(e)
        
        # Try fallback
        if fallback_func:
            try:
                logger.info(f"Using fallback for {service_name}")
                result = await fallback_func(*args, **kwargs)
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise fallback_error
        else:
            raise e


class TimeoutHandler:
    """Handle timeouts gracefully"""
    
    @staticmethod
    async def with_timeout(
        coro,
        timeout: float,
        fallback_value: Any = None
    ) -> Any:
        """Execute coroutine with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Operation timed out after {timeout}s")
            if fallback_value is not None:
                return fallback_value
            raise
    
    @staticmethod
    async def with_progressive_timeout(
        funcs: list[tuple[Callable, float]],
        fallback_value: Any = None
    ) -> Any:
        """
        Try functions with increasing timeouts
        
        Args:
            funcs: List of (function, timeout) tuples
            fallback_value: Value to return if all fail
        
        Returns:
            Result from first successful function
        """
        for func, timeout in funcs:
            try:
                return await asyncio.wait_for(func(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Function timed out after {timeout}s, trying next")
                continue
            except Exception as e:
                logger.error(f"Function failed: {e}, trying next")
                continue
        
        # All failed
        if fallback_value is not None:
            return fallback_value
        raise Exception("All functions failed or timed out")


class PartialResultHandler:
    """Handle partial results"""
    
    @staticmethod
    async def gather_with_partial(
        tasks: list,
        min_required: int = 1
    ) -> tuple[list, list]:
        """
        Gather results, accepting partial success
        
        Args:
            tasks: List of coroutines
            min_required: Minimum successful results required
        
        Returns:
            (successful_results, errors)
        """
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = []
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
            else:
                successful.append(result)
        
        if len(successful) < min_required:
            raise Exception(
                f"Only {len(successful)}/{len(tasks)} tasks succeeded. "
                f"Required: {min_required}"
            )
        
        return successful, errors
    
    @staticmethod
    async def race_with_fallback(
        primary_task,
        fallback_task,
        primary_timeout: float = 5.0
    ) -> Any:
        """
        Race primary task with fallback
        
        If primary doesn't complete in time, use fallback
        """
        try:
            # Try primary with timeout
            return await asyncio.wait_for(primary_task, timeout=primary_timeout)
        except asyncio.TimeoutError:
            logger.warning("Primary task timed out, using fallback")
            return await fallback_task


# Convenience decorators
def with_fallback(fallback_func: Callable):
    """Decorator for graceful degradation"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            service_name = func.__name__
            return await with_graceful_degradation(
                service_name,
                lambda: func(*args, **kwargs),
                lambda: fallback_func(*args, **kwargs) if fallback_func else None
            )
        return wrapper
    return decorator
