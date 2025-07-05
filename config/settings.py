"""
Configuration settings for the web scraper
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class ScrapingConfig:
    """Main configuration class for scraping settings"""
    
    # Basic settings
    base_delay: float = 1.0
    max_delay: float = 5.0
    timeout: int = 30
    max_retries: int = 3
    concurrent_requests: int = 10
    
    # User agents
    user_agents: List[str] = field(default_factory=lambda: [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
    ])
    
    # Headers
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    })
    
    # Proxy settings
    use_proxies: bool = False
    proxy_list: List[str] = field(default_factory=list)
    proxy_rotation: bool = True
    
    # Rate limiting
    respect_robots_txt: bool = True
    crawl_delay: Optional[float] = None
    
    # Storage settings
    output_dir: str = "output"
    data_formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    
    # Database settings
    database_url: Optional[str] = None
    mongodb_url: Optional[str] = None
    redis_url: Optional[str] = None
    
    # Browser automation
    headless: bool = True
    browser_type: str = "chrome"  # chrome, firefox, safari
    page_load_strategy: str = "normal"  # normal, eager, none
    
    # CAPTCHA solving
    captcha_service: Optional[str] = None  # 2captcha, anticaptcha
    captcha_api_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "scraper.log"
    
    # Monitoring
    enable_metrics: bool = False
    metrics_port: int = 8000

# Environment-based configuration
class Config:
    """Environment configuration"""
    
    # API Keys
    CAPTCHA_API_KEY = os.getenv('CAPTCHA_API_KEY')
    PROXY_API_KEY = os.getenv('PROXY_API_KEY')
    
    # Database URLs
    DATABASE_URL = os.getenv('DATABASE_URL')
    MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Directories
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / "output"
    LOGS_DIR = BASE_DIR / "logs"
    CACHE_DIR = BASE_DIR / "cache"
    
    # Create directories if they don't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)
    
    # Scraping limits
    MAX_PAGES_PER_DOMAIN = int(os.getenv('MAX_PAGES_PER_DOMAIN', 1000))
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', 10))
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', 1.0))
    
    # Browser settings
    BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', 30))
    HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'

# Default scraping configuration
DEFAULT_CONFIG = ScrapingConfig()