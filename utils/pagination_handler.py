"""
Pagination handling utilities
"""
import re
from typing import List, Optional, Dict, Any, Callable
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from loguru import logger

from bs4 import BeautifulSoup


class PaginationHandler:
    """
    Handle different types of pagination patterns
    """
    
    def __init__(self):
        self.pagination_patterns = {
            'next_link': [
                'a[rel="next"]',
                'a.next',
                'a.pagination-next',
                'a[aria-label*="next" i]',
                'a[title*="next" i]',
                'a:contains("Next")',
                'a:contains(">")',
                'a:contains("→")'
            ],
            'page_numbers': [
                '.pagination a',
                '.pager a',
                '.page-numbers a',
                'nav[aria-label*="pagination" i] a'
            ],
            'load_more': [
                'button[data-load-more]',
                'a[data-load-more]',
                '.load-more',
                'button:contains("Load More")',
                'button:contains("Show More")'
            ]
        }
    
    def detect_pagination_type(self, soup: BeautifulSoup) -> str:
        """Detect the type of pagination used on the page"""
        
        # Check for next link pagination
        for selector in self.pagination_patterns['next_link']:
            if soup.select(selector):
                return 'next_link'
        
        # Check for numbered pagination
        for selector in self.pagination_patterns['page_numbers']:
            elements = soup.select(selector)
            if len(elements) > 1:  # Multiple page links
                return 'page_numbers'
        
        # Check for load more button
        for selector in self.pagination_patterns['load_more']:
            if soup.select(selector):
                return 'load_more'
        
        # Check for infinite scroll indicators
        infinite_scroll_indicators = [
            '[data-infinite-scroll]',
            '.infinite-scroll',
            '[data-scroll-loading]'
        ]
        
        for selector in infinite_scroll_indicators:
            if soup.select(selector):
                return 'infinite_scroll'
        
        return 'none'
    
    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Get the URL of the next page"""
        
        # Try different next link selectors
        for selector in self.pagination_patterns['next_link']:
            elements = soup.select(selector)
            if elements:
                href = elements[0].get('href')
                if href:
                    return urljoin(current_url, href)
        
        return None
    
    def get_all_page_urls(
        self, 
        soup: BeautifulSoup, 
        current_url: str,
        max_pages: Optional[int] = None
    ) -> List[str]:
        """Get URLs of all pages from numbered pagination"""
        
        page_urls = []
        
        for selector in self.pagination_patterns['page_numbers']:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    href = element.get('href')
                    if href:
                        full_url = urljoin(current_url, href)
                        if full_url not in page_urls:
                            page_urls.append(full_url)
                
                # Limit number of pages if specified
                if max_pages and len(page_urls) >= max_pages:
                    page_urls = page_urls[:max_pages]
                
                break
        
        return page_urls
    
    def generate_page_urls(
        self, 
        base_url: str, 
        page_param: str = 'page',
        start_page: int = 1,
        max_pages: Optional[int] = None
    ) -> List[str]:
        """Generate page URLs using URL parameters"""
        
        urls = []
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        
        page = start_page
        while True:
            if max_pages and page > start_page + max_pages - 1:
                break
            
            # Update page parameter
            query_params[page_param] = [str(page)]
            
            # Reconstruct URL
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            urls.append(new_url)
            page += 1
        
        return urls
    
    def extract_page_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract pagination information from the page"""
        
        info = {
            'current_page': None,
            'total_pages': None,
            'has_next': False,
            'has_previous': False,
            'pagination_type': self.detect_pagination_type(soup)
        }
        
        # Try to extract current page number
        current_page_selectors = [
            '.pagination .current',
            '.pagination .active',
            '.page-numbers.current',
            '[aria-current="page"]'
        ]
        
        for selector in current_page_selectors:
            elements = soup.select(selector)
            if elements:
                text = elements[0].get_text(strip=True)
                try:
                    info['current_page'] = int(text)
                    break
                except ValueError:
                    continue
        
        # Try to extract total pages
        total_pages_patterns = [
            r'Page\s+\d+\s+of\s+(\d+)',
            r'(\d+)\s+pages?',
            r'Showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)'
        ]
        
        page_text = soup.get_text()
        for pattern in total_pages_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    info['total_pages'] = int(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Check for next/previous links
        info['has_next'] = bool(self.get_next_page_url(soup, ''))
        
        prev_selectors = [
            'a[rel="prev"]',
            'a.prev',
            'a.pagination-prev',
            'a:contains("Previous")',
            'a:contains("<")',
            'a:contains("←")'
        ]
        
        for selector in prev_selectors:
            if soup.select(selector):
                info['has_previous'] = True
                break
        
        return info
    
    def should_continue_pagination(
        self, 
        current_page: int, 
        max_pages: Optional[int] = None,
        has_next: bool = True
    ) -> bool:
        """Determine if pagination should continue"""
        
        if not has_next:
            return False
        
        if max_pages and current_page >= max_pages:
            return False
        
        return True
    
    def extract_pagination_urls_from_sitemap(self, sitemap_content: str) -> List[str]:
        """Extract URLs from XML sitemap"""
        
        urls = []
        
        try:
            soup = BeautifulSoup(sitemap_content, 'xml')
            
            # Extract URLs from sitemap
            for url_element in soup.find_all('url'):
                loc = url_element.find('loc')
                if loc:
                    urls.append(loc.get_text(strip=True))
            
            # Extract URLs from sitemap index
            for sitemap_element in soup.find_all('sitemap'):
                loc = sitemap_element.find('loc')
                if loc:
                    urls.append(loc.get_text(strip=True))
            
        except Exception as e:
            logger.error(f"Error parsing sitemap: {e}")
        
        return urls