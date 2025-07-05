"""
Rate limiting utilities
"""
import asyncio
import time
from typing import Optional
from loguru import logger


class RateLimiter:
    """
    Rate limiter for controlling request frequency
    """
    
    def __init__(self, config):
        self.config = config
        self.last_request_time = 0
        self.request_count = 0
        self.window_start = time.time()
        
    def wait_sync(self):
        """Synchronous rate limiting"""
        current_time = time.time()
        
        # Calculate delay based on configuration
        time_since_last = current_time - self.last_request_time
        min_delay = self.config.base_delay
        
        if hasattr(self.config, 'crawl_delay') and self.config.crawl_delay:
            min_delay = max(min_delay, self.config.crawl_delay)
        
        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    async def wait_async(self):
        """Asynchronous rate limiting"""
        current_time = time.time()
        
        # Calculate delay based on configuration
        time_since_last = current_time - self.last_request_time
        min_delay = self.config.base_delay
        
        if hasattr(self.config, 'crawl_delay') and self.config.crawl_delay:
            min_delay = max(min_delay, self.config.crawl_delay)
        
        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def get_stats(self) -> dict:
        """Get rate limiting statistics"""
        current_time = time.time()
        window_duration = current_time - self.window_start
        
        return {
            'total_requests': self.request_count,
            'window_duration': window_duration,
            'requests_per_second': self.request_count / window_duration if window_duration > 0 else 0,
            'last_request_time': self.last_request_time
        }