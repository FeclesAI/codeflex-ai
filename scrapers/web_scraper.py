"""
Main web scraper class combining all functionality
"""
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable
from urllib.parse import urljoin, urlparse

from loguru import logger

from core.html_scraper import HTMLScraper
from core.browser_scraper import BrowserScraper
from utils.data_processor import DataProcessor
from utils.pagination_handler import PaginationHandler
from config.settings import ScrapingConfig, Config


class WebScraper:
    """
    Comprehensive web scraper with all features
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.html_scraper = HTMLScraper(self.config)
        self.browser_scraper = BrowserScraper(self.config)
        self.data_processor = DataProcessor()
        self.pagination_handler = PaginationHandler()
        
        # Results storage
        self.results = []
        self.errors = []
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logger.remove()  # Remove default handler
        
        # Add file handler
        log_file = Config.LOGS_DIR / self.config.log_file
        logger.add(
            log_file,
            level=self.config.log_level,
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
        )
        
        # Add console handler
        logger.add(
            lambda msg: print(msg, end=''),
            level=self.config.log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}"
        )
    
    def scrape_single_url(
        self,
        url: str,
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        use_browser: bool = False,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single URL"""
        
        logger.info(f"Scraping: {url}")
        
        try:
            if use_browser:
                result = self.browser_scraper.scrape_sync(url, **kwargs)
                
                # If we got page source, parse it with HTML scraper
                if result and 'page_source' in result and selectors:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result['page_source'], 'lxml')
                    extracted_data = self.html_scraper.extract_data(soup, selectors, url)
                    result['data'] = extracted_data
            else:
                result = self.html_scraper.scrape_sync(url, selectors, **kwargs)
            
            if result:
                # Check for duplicates
                if not self.data_processor.is_duplicate(result):
                    self.results.append(result)
                    logger.success(f"Successfully scraped: {url}")
                else:
                    logger.warning(f"Duplicate content detected: {url}")
                
                return result
            else:
                logger.error(f"Failed to scrape: {url}")
                self.errors.append({'url': url, 'error': 'No result returned'})
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            self.errors.append({'url': url, 'error': str(e)})
        
        return None
    
    async def scrape_single_url_async(
        self,
        url: str,
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        use_browser: bool = False,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single URL asynchronously"""
        
        logger.info(f"Scraping async: {url}")
        
        try:
            if use_browser:
                result = await self.browser_scraper.scrape_async(url, **kwargs)
                
                # If we got page source, parse it with HTML scraper
                if result and 'page_source' in result and selectors:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result['page_source'], 'lxml')
                    extracted_data = self.html_scraper.extract_data(soup, selectors, url)
                    result['data'] = extracted_data
            else:
                result = await self.html_scraper.scrape_async(url, selectors, **kwargs)
            
            if result:
                # Check for duplicates
                if not self.data_processor.is_duplicate(result):
                    self.results.append(result)
                    logger.success(f"Successfully scraped: {url}")
                else:
                    logger.warning(f"Duplicate content detected: {url}")
                
                return result
            else:
                logger.error(f"Failed to scrape: {url}")
                self.errors.append({'url': url, 'error': 'No result returned'})
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            self.errors.append({'url': url, 'error': str(e)})
        
        return None
    
    def scrape_multiple_urls(
        self,
        urls: List[str],
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        use_browser: bool = False,
        max_concurrent: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Scrape multiple URLs with concurrency control"""
        
        logger.info(f"Starting to scrape {len(urls)} URLs")
        
        # Run async scraping
        return asyncio.run(self.scrape_multiple_urls_async(
            urls, selectors, use_browser, max_concurrent, **kwargs
        ))
    
    async def scrape_multiple_urls_async(
        self,
        urls: List[str],
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        use_browser: bool = False,
        max_concurrent: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Scrape multiple URLs asynchronously"""
        
        max_concurrent = max_concurrent or self.config.concurrent_requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_single_url_async(
                    url, selectors, use_browser, **kwargs
                )
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid results
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception in concurrent scraping: {result}")
        
        logger.info(f"Completed scraping {len(valid_results)} URLs successfully")
        return valid_results
    
    def scrape_with_pagination(
        self,
        start_url: str,
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        max_pages: Optional[int] = None,
        use_browser: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Scrape website with pagination support"""
        
        logger.info(f"Starting pagination scraping from: {start_url}")
        
        current_url = start_url
        page_count = 0
        all_results = []
        
        while current_url and (not max_pages or page_count < max_pages):
            page_count += 1
            logger.info(f"Scraping page {page_count}: {current_url}")
            
            # Scrape current page
            result = self.scrape_single_url(current_url, selectors, use_browser, **kwargs)
            
            if result:
                all_results.append(result)
                
                # Get next page URL
                if 'page_source' in result:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result['page_source'], 'lxml')
                elif use_browser:
                    # Get page source from browser
                    page_source = self.browser_scraper._driver.page_source if self.browser_scraper._driver else None
                    if page_source:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(page_source, 'lxml')
                    else:
                        break
                else:
                    # Make another request to get the page for pagination analysis
                    response = self.html_scraper._make_request_sync(current_url)
                    if response:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, 'lxml')
                    else:
                        break
                
                # Find next page
                next_url = self.pagination_handler.get_next_page_url(soup, current_url)
                
                if next_url and next_url != current_url:
                    current_url = next_url
                else:
                    logger.info("No more pages found")
                    break
            else:
                logger.error(f"Failed to scrape page {page_count}")
                break
            
            # Add delay between pages
            time.sleep(self.config.base_delay)
        
        logger.info(f"Pagination scraping completed. Scraped {len(all_results)} pages")
        return all_results
    
    def scrape_sitemap(
        self,
        sitemap_url: str,
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        url_filter: Optional[Callable[[str], bool]] = None,
        max_urls: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Scrape URLs from sitemap"""
        
        logger.info(f"Scraping sitemap: {sitemap_url}")
        
        # Get sitemap content
        response = self.html_scraper._make_request_sync(sitemap_url)
        if not response:
            logger.error(f"Failed to fetch sitemap: {sitemap_url}")
            return []
        
        # Extract URLs from sitemap
        urls = self.pagination_handler.extract_pagination_urls_from_sitemap(response.text)
        
        # Apply URL filter
        if url_filter:
            urls = [url for url in urls if url_filter(url)]
        
        # Limit number of URLs
        if max_urls:
            urls = urls[:max_urls]
        
        logger.info(f"Found {len(urls)} URLs in sitemap")
        
        # Scrape all URLs
        return self.scrape_multiple_urls(urls, selectors, **kwargs)
    
    def fill_and_submit_form(
        self,
        url: str,
        form_data: Dict[str, str],
        submit: bool = True,
        wait_after_submit: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        """Fill and submit a form"""
        
        logger.info(f"Filling form on: {url}")
        
        # Navigate to the page
        result = self.browser_scraper.scrape_sync(url)
        if not result:
            logger.error(f"Failed to load page: {url}")
            return None
        
        # Fill and submit form
        success = self.browser_scraper.fill_form(form_data, submit)
        
        if success:
            if submit:
                # Wait for page to load after submission
                time.sleep(wait_after_submit)
                
                # Get the result page
                if self.browser_scraper._driver:
                    current_url = self.browser_scraper._driver.current_url
                    page_source = self.browser_scraper._driver.page_source
                    title = self.browser_scraper._driver.title
                    
                    return {
                        'url': current_url,
                        'original_url': url,
                        'title': title,
                        'page_source': page_source,
                        'form_submitted': True,
                        'timestamp': time.time()
                    }
            
            logger.success("Form filled successfully")
            return result
        else:
            logger.error("Failed to fill form")
            return None
    
    def save_results(
        self,
        output_dir: Optional[str] = None,
        formats: Optional[List[str]] = None
    ):
        """Save scraping results to files"""
        
        if not self.results:
            logger.warning("No results to save")
            return
        
        output_dir = Path(output_dir or self.config.output_dir)
        formats = formats or self.config.data_formats
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        for format_type in formats:
            if format_type.lower() == 'json':
                filepath = output_dir / f"scraping_results_{timestamp}.json"
                self.data_processor.save_to_json(self.results, filepath)
            
            elif format_type.lower() == 'csv':
                filepath = output_dir / f"scraping_results_{timestamp}.csv"
                self.data_processor.save_to_csv(self.results, filepath)
            
            elif format_type.lower() == 'excel':
                filepath = output_dir / f"scraping_results_{timestamp}.xlsx"
                self.data_processor.save_to_excel(self.results, filepath)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive scraping statistics"""
        
        html_stats = self.html_scraper.get_stats()
        browser_stats = self.browser_scraper.get_stats()
        duplicate_stats = self.data_processor.get_duplicate_stats()
        
        return {
            'html_scraper': html_stats,
            'browser_scraper': browser_stats,
            'duplicate_detection': duplicate_stats,
            'results_count': len(self.results),
            'errors_count': len(self.errors),
            'total_processed': len(self.results) + len(self.errors)
        }
    
    def close(self):
        """Close all resources"""
        self.html_scraper.session_manager.close()
        self.browser_scraper.close()
        
        if self.html_scraper.proxy_manager:
            self.html_scraper.proxy_manager.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()