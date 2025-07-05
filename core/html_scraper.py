"""
HTML scraper with BeautifulSoup integration
"""
import asyncio
import re
from typing import Dict, List, Optional, Union, Any, Callable
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger

from core.base_scraper import BaseScraper
from utils.data_processor import DataProcessor
from utils.pagination_handler import PaginationHandler


class HTMLScraper(BaseScraper):
    """
    HTML scraper using BeautifulSoup for parsing
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self.data_processor = DataProcessor()
        self.pagination_handler = PaginationHandler()
        
    def _parse_html(self, html_content: str, parser: str = 'lxml') -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup"""
        try:
            soup = BeautifulSoup(html_content, parser)
            return soup
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            # Fallback to html.parser
            return BeautifulSoup(html_content, 'html.parser')
    
    def extract_data(
        self,
        soup: BeautifulSoup,
        selectors: Dict[str, Union[str, Dict[str, Any]]],
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract data using CSS selectors or XPath
        
        Args:
            soup: BeautifulSoup object
            selectors: Dictionary of field names and their selectors
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Dictionary of extracted data
        """
        extracted_data = {}
        
        for field_name, selector_config in selectors.items():
            try:
                if isinstance(selector_config, str):
                    # Simple CSS selector
                    elements = soup.select(selector_config)
                    if elements:
                        if len(elements) == 1:
                            extracted_data[field_name] = self._extract_element_data(
                                elements[0], base_url
                            )
                        else:
                            extracted_data[field_name] = [
                                self._extract_element_data(elem, base_url) 
                                for elem in elements
                            ]
                    else:
                        extracted_data[field_name] = None
                        
                elif isinstance(selector_config, dict):
                    # Advanced selector configuration
                    selector = selector_config.get('selector')
                    attribute = selector_config.get('attribute', 'text')
                    multiple = selector_config.get('multiple', False)
                    transform = selector_config.get('transform')
                    default = selector_config.get('default')
                    
                    elements = soup.select(selector)
                    
                    if elements:
                        if multiple:
                            values = []
                            for elem in elements:
                                value = self._extract_element_data(elem, base_url, attribute)
                                if transform and callable(transform):
                                    value = transform(value)
                                values.append(value)
                            extracted_data[field_name] = values
                        else:
                            value = self._extract_element_data(elements[0], base_url, attribute)
                            if transform and callable(transform):
                                value = transform(value)
                            extracted_data[field_name] = value
                    else:
                        extracted_data[field_name] = default
                        
            except Exception as e:
                logger.error(f"Error extracting {field_name}: {e}")
                extracted_data[field_name] = None
        
        return extracted_data
    
    def _extract_element_data(
        self, 
        element: Tag, 
        base_url: Optional[str] = None, 
        attribute: str = 'text'
    ) -> str:
        """Extract data from a BeautifulSoup element"""
        
        if attribute == 'text':
            return element.get_text(strip=True)
        elif attribute == 'html':
            return str(element)
        elif attribute.startswith('attr:'):
            attr_name = attribute[5:]  # Remove 'attr:' prefix
            value = element.get(attr_name, '')
            
            # Resolve relative URLs
            if base_url and attr_name in ['href', 'src', 'action'] and value:
                value = urljoin(base_url, value)
                
            return value
        else:
            return element.get(attribute, '')
    
    def extract_links(
        self, 
        soup: BeautifulSoup, 
        base_url: str,
        link_filter: Optional[Callable[[str], bool]] = None
    ) -> List[str]:
        """Extract all links from the page"""
        
        links = []
        
        # Extract from <a> tags
        for link in soup.find_all('a', href=True):
            url = urljoin(base_url, link['href'])
            if not link_filter or link_filter(url):
                links.append(url)
        
        # Extract from <link> tags
        for link in soup.find_all('link', href=True):
            url = urljoin(base_url, link['href'])
            if not link_filter or link_filter(url):
                links.append(url)
        
        return list(set(links))  # Remove duplicates
    
    def extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all images from the page"""
        
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                image_data = {
                    'src': urljoin(base_url, src),
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'width': img.get('width', ''),
                    'height': img.get('height', '')
                }
                images.append(image_data)
        
        return images
    
    def extract_forms(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract all forms from the page"""
        
        forms = []
        
        for form in soup.find_all('form'):
            form_data = {
                'action': urljoin(base_url, form.get('action', '')),
                'method': form.get('method', 'GET').upper(),
                'enctype': form.get('enctype', 'application/x-www-form-urlencoded'),
                'fields': []
            }
            
            # Extract form fields
            for field in form.find_all(['input', 'select', 'textarea']):
                field_data = {
                    'name': field.get('name', ''),
                    'type': field.get('type', 'text'),
                    'value': field.get('value', ''),
                    'required': field.has_attr('required')
                }
                
                if field.name == 'select':
                    options = []
                    for option in field.find_all('option'):
                        options.append({
                            'value': option.get('value', ''),
                            'text': option.get_text(strip=True)
                        })
                    field_data['options'] = options
                
                form_data['fields'].append(field_data)
            
            forms.append(form_data)
        
        return forms
    
    async def scrape_async(
        self, 
        url: str, 
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        extract_links: bool = False,
        extract_images: bool = False,
        extract_forms: bool = False,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single URL asynchronously"""
        
        response = await self._make_request_async(url, **kwargs)
        if not response:
            return None
        
        try:
            html_content = await response.text()
            soup = self._parse_html(html_content)
            
            result = {
                'url': url,
                'status_code': response.status,
                'title': soup.title.string if soup.title else '',
                'timestamp': self.data_processor.get_timestamp()
            }
            
            # Extract data using selectors
            if selectors:
                extracted_data = self.extract_data(soup, selectors, url)
                result['data'] = extracted_data
                self.stats['data_extracted'] += len(extracted_data)
            
            # Extract links if requested
            if extract_links:
                result['links'] = self.extract_links(soup, url)
            
            # Extract images if requested
            if extract_images:
                result['images'] = self.extract_images(soup, url)
            
            # Extract forms if requested
            if extract_forms:
                result['forms'] = self.extract_forms(soup, url)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing response from {url}: {e}")
            return None
    
    def scrape_sync(
        self, 
        url: str, 
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        extract_links: bool = False,
        extract_images: bool = False,
        extract_forms: bool = False,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single URL synchronously"""
        
        response = self._make_request_sync(url, **kwargs)
        if not response:
            return None
        
        try:
            soup = self._parse_html(response.text)
            
            result = {
                'url': url,
                'status_code': response.status_code,
                'title': soup.title.string if soup.title else '',
                'timestamp': self.data_processor.get_timestamp()
            }
            
            # Extract data using selectors
            if selectors:
                extracted_data = self.extract_data(soup, selectors, url)
                result['data'] = extracted_data
                self.stats['data_extracted'] += len(extracted_data)
            
            # Extract links if requested
            if extract_links:
                result['links'] = self.extract_links(soup, url)
            
            # Extract images if requested
            if extract_images:
                result['images'] = self.extract_images(soup, url)
            
            # Extract forms if requested
            if extract_forms:
                result['forms'] = self.extract_forms(soup, url)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing response from {url}: {e}")
            return None
    
    async def scrape_multiple_async(
        self, 
        urls: List[str], 
        selectors: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
        max_concurrent: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Scrape multiple URLs concurrently"""
        
        max_concurrent = max_concurrent or self.config.concurrent_requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_async(url, selectors, **kwargs)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception in concurrent scraping: {result}")
        
        return valid_results