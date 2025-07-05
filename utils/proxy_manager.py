"""
Proxy management utilities
"""
import random
import time
from typing import List, Optional, Dict
from loguru import logger


class ProxyManager:
    """
    Proxy rotation and management
    """
    
    def __init__(self, config):
        self.config = config
        self.proxies = config.proxy_list.copy() if config.proxy_list else []
        self.current_proxy_index = 0
        self.proxy_stats = {}
        
        # Initialize proxy statistics
        for proxy in self.proxies:
            self.proxy_stats[proxy] = {
                'requests': 0,
                'failures': 0,
                'last_used': 0,
                'response_time': 0,
                'active': True
            }
    
    def add_proxy(self, proxy: str):
        """Add a new proxy to the pool"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            self.proxy_stats[proxy] = {
                'requests': 0,
                'failures': 0,
                'last_used': 0,
                'response_time': 0,
                'active': True
            }
            logger.info(f"Added proxy: {proxy}")
    
    def remove_proxy(self, proxy: str):
        """Remove a proxy from the pool"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            if proxy in self.proxy_stats:
                del self.proxy_stats[proxy]
            logger.info(f"Removed proxy: {proxy}")
    
    def get_proxy(self) -> Optional[str]:
        """Get the next proxy in rotation"""
        if not self.proxies:
            return None
        
        active_proxies = [p for p in self.proxies if self.proxy_stats[p]['active']]
        
        if not active_proxies:
            logger.warning("No active proxies available")
            return None
        
        if self.config.proxy_rotation:
            # Round-robin rotation
            proxy = active_proxies[self.current_proxy_index % len(active_proxies)]
            self.current_proxy_index += 1
        else:
            # Random selection
            proxy = random.choice(active_proxies)
        
        # Update statistics
        self.proxy_stats[proxy]['requests'] += 1
        self.proxy_stats[proxy]['last_used'] = time.time()
        
        logger.debug(f"Using proxy: {proxy}")
        return proxy
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed"""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]['failures'] += 1
            
            # Disable proxy if too many failures
            failure_rate = (
                self.proxy_stats[proxy]['failures'] / 
                max(1, self.proxy_stats[proxy]['requests'])
            )
            
            if failure_rate > 0.5 and self.proxy_stats[proxy]['requests'] > 5:
                self.proxy_stats[proxy]['active'] = False
                logger.warning(f"Disabled proxy due to high failure rate: {proxy}")
    
    def mark_proxy_success(self, proxy: str, response_time: float):
        """Mark a proxy as successful"""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]['response_time'] = response_time
    
    def get_proxy_stats(self) -> Dict[str, Dict]:
        """Get proxy statistics"""
        return self.proxy_stats.copy()
    
    def reset_proxy_stats(self):
        """Reset all proxy statistics"""
        for proxy in self.proxy_stats:
            self.proxy_stats[proxy] = {
                'requests': 0,
                'failures': 0,
                'last_used': 0,
                'response_time': 0,
                'active': True
            }
        logger.info("Reset proxy statistics")
    
    def close(self):
        """Cleanup proxy manager"""
        logger.info("Proxy manager closed")