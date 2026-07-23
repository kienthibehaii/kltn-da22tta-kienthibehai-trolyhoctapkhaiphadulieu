# rate_limiter.py - Rate limiter cho Gemini API
import time
from collections import deque
from threading import Lock

class RateLimiter:
    def __init__(self, max_requests=15, time_window=60):
        """
        max_requests: số request tối đa
        time_window: trong khoảng thời gian (giây)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Đợi nếu vượt quá rate limit"""
        with self.lock:
            now = time.time()
            
            # Xóa requests cũ
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # Nếu đã đủ requests, đợi
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    print(f"⏳ Rate limit reached, waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    return self.wait_if_needed()
            
            # Thêm request mới
            self.requests.append(now)

# Global rate limiter
gemini_rate_limiter = RateLimiter(max_requests=15, time_window=60)
