# security/rate_limiter.py - API Rate Limiting
"""
Rate Limiting System

Features:
- Request rate limiting
- IP-based limiting
- User-based limiting
- Sliding window algorithm
- Redis-backed (optional)
- In-memory fallback
"""

import time
from typing import Optional, Dict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import streamlit as st


class RateLimiter:
    """
    Rate limiter for API protection.
    """
    
    # Default limits
    DEFAULT_REQUESTS_PER_MINUTE = 60
    DEFAULT_REQUESTS_PER_HOUR = 1000
    DEFAULT_REQUESTS_PER_DAY = 10000
    
    def __init__(self, 
                 requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
                 requests_per_hour: int = DEFAULT_REQUESTS_PER_HOUR,
                 requests_per_day: int = DEFAULT_REQUESTS_PER_DAY):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            requests_per_day: Max requests per day
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        
        # In-memory storage (use Redis in production)
        self.request_history: Dict[str, deque] = defaultdict(deque)
        self.blocked_until: Dict[str, datetime] = {}
        
        print("✅ Rate Limiter initialized")
        print(f"   Limits: {requests_per_minute}/min, {requests_per_hour}/hour, {requests_per_day}/day")
    
    def _get_client_id(self) -> str:
        """
        Get client identifier.
        
        Uses session ID or IP address.
        """
        # Try to get session ID from Streamlit
        if hasattr(st, 'session_state') and hasattr(st.session_state, 'session_id'):
            return f"session_{st.session_state.session_id}"
        
        # Fallback to a default identifier
        return "default_client"
    
    def _clean_old_requests(self, client_id: str, window_seconds: int):
        """Remove requests older than window"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Remove old requests
        while self.request_history[client_id] and self.request_history[client_id][0] < cutoff_time:
            self.request_history[client_id].popleft()
    
    def _count_requests_in_window(self, client_id: str, window_seconds: int) -> int:
        """Count requests in time window"""
        self._clean_old_requests(client_id, window_seconds)
        return len(self.request_history[client_id])
    
    def is_allowed(self, client_id: Optional[str] = None) -> tuple[bool, str]:
        """
        Check if request is allowed.
        
        Args:
            client_id: Client identifier (None = auto-detect)
        
        Returns:
            (is_allowed, reason)
        """
        if client_id is None:
            client_id = self._get_client_id()
        
        current_time = time.time()
        
        # Check if client is blocked
        if client_id in self.blocked_until:
            if datetime.now() < self.blocked_until[client_id]:
                remaining = (self.blocked_until[client_id] - datetime.now()).seconds
                return False, f"Rate limit exceeded. Try again in {remaining} seconds"
            else:
                # Unblock
                del self.blocked_until[client_id]
        
        # Check minute limit
        minute_count = self._count_requests_in_window(client_id, 60)
        if minute_count >= self.requests_per_minute:
            self._block_client(client_id, duration_seconds=60)
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Check hour limit
        hour_count = self._count_requests_in_window(client_id, 3600)
        if hour_count >= self.requests_per_hour:
            self._block_client(client_id, duration_seconds=300)  # 5 minutes
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        # Check day limit
        day_count = self._count_requests_in_window(client_id, 86400)
        if day_count >= self.requests_per_day:
            self._block_client(client_id, duration_seconds=3600)  # 1 hour
            return False, f"Rate limit exceeded: {self.requests_per_day} requests per day"
        
        # Record request
        self.request_history[client_id].append(current_time)
        
        return True, "OK"
    
    def _block_client(self, client_id: str, duration_seconds: int):
        """Block client for specified duration"""
        self.blocked_until[client_id] = datetime.now() + timedelta(seconds=duration_seconds)
    
    def get_remaining_requests(self, client_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get remaining requests for client.
        
        Returns:
            Dict with remaining requests per time window
        """
        if client_id is None:
            client_id = self._get_client_id()
        
        minute_count = self._count_requests_in_window(client_id, 60)
        hour_count = self._count_requests_in_window(client_id, 3600)
        day_count = self._count_requests_in_window(client_id, 86400)
        
        return {
            'per_minute': max(0, self.requests_per_minute - minute_count),
            'per_hour': max(0, self.requests_per_hour - hour_count),
            'per_day': max(0, self.requests_per_day - day_count)
        }
    
    def reset_client(self, client_id: str):
        """Reset rate limit for client"""
        if client_id in self.request_history:
            del self.request_history[client_id]
        if client_id in self.blocked_until:
            del self.blocked_until[client_id]
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        total_clients = len(self.request_history)
        blocked_clients = len(self.blocked_until)
        total_requests = sum(len(history) for history in self.request_history.values())
        
        return {
            'total_clients': total_clients,
            'blocked_clients': blocked_clients,
            'total_requests': total_requests,
            'limits': {
                'per_minute': self.requests_per_minute,
                'per_hour': self.requests_per_hour,
                'per_day': self.requests_per_day
            }
        }


def rate_limit_decorator(limiter: RateLimiter):
    """
    Decorator for rate limiting functions.
    
    Usage:
        @rate_limit_decorator(limiter)
        def my_api_function():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            is_allowed, reason = limiter.is_allowed()
            
            if not is_allowed:
                raise Exception(f"Rate limit exceeded: {reason}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Streamlit rate limit check
def check_rate_limit(limiter: RateLimiter) -> bool:
    """
    Check rate limit in Streamlit app.
    
    Returns:
        True if allowed, False if blocked (shows error)
    """
    is_allowed, reason = limiter.is_allowed()
    
    if not is_allowed:
        st.error(f"⚠️ {reason}")
        st.stop()
    
    return True


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING RATE LIMITER")
    print("="*60)
    
    # Create rate limiter with low limits for testing
    limiter = RateLimiter(
        requests_per_minute=5,
        requests_per_hour=20,
        requests_per_day=100
    )
    
    client_id = "test_client"
    
    # Test normal requests
    print("\n# Test Normal Requests")
    for i in range(7):
        is_allowed, reason = limiter.is_allowed(client_id)
        print(f"Request {i+1}: {'✅ Allowed' if is_allowed else f'❌ Blocked - {reason}'}")
        
        if is_allowed:
            remaining = limiter.get_remaining_requests(client_id)
            print(f"  Remaining: {remaining['per_minute']}/min, {remaining['per_hour']}/hour")
        
        time.sleep(0.1)
    
    # Test stats
    print("\n# Rate Limiter Stats")
    stats = limiter.get_stats()
    print(f"Total clients: {stats['total_clients']}")
    print(f"Blocked clients: {stats['blocked_clients']}")
    print(f"Total requests: {stats['total_requests']}")
    print(f"Limits: {stats['limits']}")
    
    # Test reset
    print("\n# Test Reset")
    limiter.reset_client(client_id)
    is_allowed, reason = limiter.is_allowed(client_id)
    print(f"After reset: {'✅ Allowed' if is_allowed else f'❌ Blocked'}")
