"""Rate limiting utilities for API calls."""
import time
from collections import defaultdict
from typing import Dict, Optional
import threading

class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self):
        self.calls: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
    
    def check_rate_limit(self, key: str, max_calls: int, window_seconds: int) -> bool:
        """
        Check if a call is allowed under the rate limit.
        
        Args:
            key: Identifier for the rate limit (e.g., 'tavily_api')
            max_calls: Maximum number of calls allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if call is allowed, False if rate limited
        """
        current_time = time.time()
        
        with self.lock:
            # Remove old calls outside the window
            self.calls[key] = [
                call_time for call_time in self.calls[key]
                if current_time - call_time < window_seconds
            ]
            
            # Check if we're under the limit
            if len(self.calls[key]) < max_calls:
                self.calls[key].append(current_time)
                return True
            
            return False
    
    def wait_if_needed(self, key: str, max_calls: int, window_seconds: int) -> None:
        """
        Wait if rate limited.
        
        Args:
            key: Identifier for the rate limit
            max_calls: Maximum number of calls allowed
            window_seconds: Time window in seconds
        """
        while not self.check_rate_limit(key, max_calls, window_seconds):
            # Calculate wait time
            with self.lock:
                if self.calls[key]:
                    oldest_call = min(self.calls[key])
                    wait_time = window_seconds - (time.time() - oldest_call) + 0.1
                    if wait_time > 0:
                        time.sleep(wait_time)
                else:
                    time.sleep(0.1)

# Global rate limiter instance
rate_limiter = RateLimiter()