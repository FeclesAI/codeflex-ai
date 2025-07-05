"""
Base scraper class with core functionality
"""
import asyncio
import random
import time
import urllib.robotparser
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urljoin, urlparse, robots

import aiohttp
import requests
from fake_useragent import UserAgent
from loguru import logger

from config.settings import ScrapingConfig, Config
from utils.rate_limiter import RateLimiter
from utils.proxy_manager import ProxyManager
from utils.session_manager import SessionManager


class BaseScraper(ABC):
    """
    Base scraper class providing core functionality for web scraping
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.session_manager = SessionManager(self.config)
        self.rate_limiter = RateLimiter(self.config)
        self.proxy_manager = ProxyManager(self.config) if self.config.use_proxies else None
        self.user_agent = UserAgent()
        
        # Robots.txt cache
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}
        
        # Statistics
        self.stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'data_extracted': 0,
            'start_time': time.time()
        }
        
        logger.info(f"Initialized {self.__class__.__name__} with config: {self.config}")
    
    def _get_robots_parser(self, url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        """Get robots.txt parser for a domain"""
        if not self.config.respect_robots_txt:
            return None
            
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if domain not in self._robots_cache:
            robots_url = urljoin(domain, '/robots.txt')
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            
            try:
                rp.read()
                self._robots_cache[domain] = rp
                logger.debug(f"Loaded robots.txt for {domain}")
            except Exception as e:
                logger.warning(f"Could not load robots.txt for {domain}: {e}")
                self._robots_cache[domain] = None
                
        return self._robots_cache[domain]
    
    def _can_fetch(self, url: str, user_agent: str = '*') -> bool:
        """Check if URL can be fetched according to robots.txt"""
        robots_parser = self._get_robots_parser(url)
        if robots_parser is None:
            return True
            
        return robots_parser.can_fetch(user_agent, url)
    
    def _get_crawl_delay(self, url: str, user_agent: str = '*') -> Optional[float]:
        """Get crawl delay from robots.txt"""
        robots_parser = self._get_robots_parser(url)
        if robots_parser is None:
            return None
            
        return robots_parser.crawl_delay(user_agent)
    
    def _prepare_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers for request"""
        headers = self.config.default_headers.copy()
        
        # Add random user agent
        if 'User-Agent' not in headers:
            if self.config.user_agents:
                headers['User-Agent'] = random.choice(self.config.user_agents)
            else:
                headers['User-Agent'] = self.user_agent.random
        
        # Add custom headers
        if custom_headers:
            headers.update(custom_headers)
            
        return headers
    
    async def _make_request_async(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[aiohttp.ClientResponse]:
        """Make asynchronous HTTP request"""
        
        # Check robots.txt
        if not self._can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None
        
        # Apply rate limiting
        await self.rate_limiter.wait_async()
        
        # Prepare headers
        request_headers = self._prepare_headers(headers)
        
        # Get proxy if enabled
        proxy = None
        if self.proxy_manager:
            proxy = self.proxy_manager.get_proxy()
        
        try:
            self.stats['requests_made'] += 1
            
            async with self.session_manager.get_async_session() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data,
                    params=params,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    **kwargs
                ) as response:
                    
                    if response.status == 200:
                        self.stats['successful_requests'] += 1
                        logger.debug(f"Successfully fetched {url}")
                        return response
                    else:
                        self.stats['failed_requests'] += 1
                        logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _make_request_sync(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[requests.Response]:
        """Make synchronous HTTP request"""
        
        # Check robots.txt
        if not self._can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None
        
        # Apply rate limiting
        self.rate_limiter.wait_sync()
        
        # Prepare headers
        request_headers = self._prepare_headers(headers)
        
        # Get proxy if enabled
        proxies = None
        if self.proxy_manager:
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                proxies = {'http': proxy, 'https': proxy}
        
        try:
            self.stats['requests_made'] += 1
            
            response = self.session_manager.get_sync_session().request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                params=params,
                proxies=proxies,
                timeout=self.config.timeout,
                **kwargs
            )
            
            if response.status_code == 200:
                self.stats['successful_requests'] += 1
                logger.debug(f"Successfully fetched {url}")
                return response
            else:
                self.stats['failed_requests'] += 1
                logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        current_time = time.time()
        runtime = current_time - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'requests_per_second': self.stats['requests_made'] / runtime if runtime > 0 else 0,
            'success_rate': (
                self.stats['successful_requests'] / self.stats['requests_made'] 
                if self.stats['requests_made'] > 0 else 0
            )
        }
    
    @abstractmethod
    async def scrape_async(self, url: str, **kwargs) -> Any:
        """Abstract method for asynchronous scraping"""
        pass
    
    @abstractmethod
    def scrape_sync(self, url: str, **kwargs) -> Any:
        """Abstract method for synchronous scraping"""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session_manager.close()
        if self.proxy_manager:
            self.proxy_manager.close()