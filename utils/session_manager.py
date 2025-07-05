"""
Session management utilities
"""
import aiohttp
import requests
from typing import Optional
from loguru import logger


class SessionManager:
    """
    HTTP session management for both sync and async requests
    """
    
    def __init__(self, config):
        self.config = config
        self._sync_session = None
        self._async_session = None
    
    def get_sync_session(self) -> requests.Session:
        """Get or create synchronous session"""
        if self._sync_session is None:
            self._sync_session = requests.Session()
            
            # Configure session
            self._sync_session.headers.update(self.config.default_headers)
            
            # Set up connection pooling
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=self.config.concurrent_requests,
                pool_maxsize=self.config.concurrent_requests * 2,
                max_retries=self.config.max_retries
            )
            
            self._sync_session.mount('http://', adapter)
            self._sync_session.mount('https://', adapter)
            
            logger.debug("Created synchronous session")
        
        return self._sync_session
    
    def get_async_session(self) -> aiohttp.ClientSession:
        """Get or create asynchronous session"""
        if self._async_session is None or self._async_session.closed:
            
            # Configure connector
            connector = aiohttp.TCPConnector(
                limit=self.config.concurrent_requests,
                limit_per_host=self.config.concurrent_requests // 2,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            # Configure timeout
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=self.config.timeout // 2
            )
            
            self._async_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.config.default_headers
            )
            
            logger.debug("Created asynchronous session")
        
        return self._async_session
    
    async def close_async_session(self):
        """Close asynchronous session"""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
            logger.debug("Closed asynchronous session")
    
    def close_sync_session(self):
        """Close synchronous session"""
        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None
            logger.debug("Closed synchronous session")
    
    def close(self):
        """Close all sessions"""
        self.close_sync_session()
        if self._async_session:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close_async_session())
                else:
                    loop.run_until_complete(self.close_async_session())
            except:
                pass