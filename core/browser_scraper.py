"""
Browser-based scraper using Selenium and Playwright
"""
import asyncio
import time
from typing import Dict, List, Optional, Union, Any, Callable
from urllib.parse import urljoin

from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Install with: pip install playwright")

from core.base_scraper import BaseScraper
from utils.captcha_solver import CaptchaSolver


class BrowserScraper(BaseScraper):
    """
    Browser-based scraper for JavaScript-heavy sites
    """
    
    def __init__(self, config=None, browser_type: str = "chrome", use_playwright: bool = False):
        super().__init__(config)
        self.browser_type = browser_type
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self.captcha_solver = CaptchaSolver(config) if config and config.captcha_service else None
        
        # Selenium driver
        self._driver = None
        
        # Playwright browser and context
        self._playwright = None
        self._browser = None
        self._context = None
    
    def _setup_selenium_driver(self) -> webdriver.Chrome:
        """Setup Selenium WebDriver"""
        
        if self.browser_type.lower() == "chrome":
            options = ChromeOptions()
            
            if self.config.headless:
                options.add_argument("--headless")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--disable-javascript")  # Can be enabled if needed
            
            # User agent
            if self.config.user_agents:
                user_agent = self.config.user_agents[0]
                options.add_argument(f"--user-agent={user_agent}")
            
            # Proxy support
            if self.proxy_manager:
                proxy = self.proxy_manager.get_proxy()
                if proxy:
                    options.add_argument(f"--proxy-server={proxy}")
            
            driver = webdriver.Chrome(options=options)
            
        elif self.browser_type.lower() == "firefox":
            options = FirefoxOptions()
            
            if self.config.headless:
                options.add_argument("--headless")
            
            # User agent
            if self.config.user_agents:
                user_agent = self.config.user_agents[0]
                options.set_preference("general.useragent.override", user_agent)
            
            driver = webdriver.Firefox(options=options)
        
        else:
            raise ValueError(f"Unsupported browser type: {self.browser_type}")
        
        # Set timeouts
        driver.implicitly_wait(self.config.timeout)
        driver.set_page_load_timeout(self.config.timeout)
        
        return driver
    
    async def _setup_playwright_browser(self) -> Browser:
        """Setup Playwright browser"""
        
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available")
        
        self._playwright = await async_playwright().start()
        
        browser_args = []
        if self.proxy_manager:
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                browser_args.extend(['--proxy-server', proxy])
        
        if self.browser_type.lower() == "chrome":
            browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                args=browser_args
            )
        elif self.browser_type.lower() == "firefox":
            browser = await self._playwright.firefox.launch(
                headless=self.config.headless,
                args=browser_args
            )
        elif self.browser_type.lower() == "safari":
            browser = await self._playwright.webkit.launch(
                headless=self.config.headless,
                args=browser_args
            )
        else:
            raise ValueError(f"Unsupported browser type: {self.browser_type}")
        
        # Create context with custom user agent
        context_options = {}
        if self.config.user_agents:
            context_options['user_agent'] = self.config.user_agents[0]
        
        self._context = await browser.new_context(**context_options)
        
        return browser
    
    def _wait_for_element(
        self, 
        driver: webdriver.Chrome, 
        selector: str, 
        by: By = By.CSS_SELECTOR,
        timeout: int = 10
    ) -> bool:
        """Wait for element to be present"""
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return True
        except TimeoutException:
            return False
    
    def _handle_captcha_selenium(self, driver: webdriver.Chrome) -> bool:
        """Handle CAPTCHA using Selenium"""
        if not self.captcha_solver:
            return False
        
        try:
            # Look for common CAPTCHA elements
            captcha_selectors = [
                "img[src*='captcha']",
                ".captcha",
                "#captcha",
                ".g-recaptcha",
                ".h-captcha"
            ]
            
            for selector in captcha_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"CAPTCHA detected: {selector}")
                    
                    # Handle image CAPTCHA
                    if "img" in selector:
                        img_element = elements[0]
                        img_src = img_element.get_attribute("src")
                        
                        if img_src:
                            solution = self.captcha_solver.solve_image_captcha(img_src)
                            if solution:
                                # Find input field and enter solution
                                input_fields = driver.find_elements(
                                    By.CSS_SELECTOR, 
                                    "input[name*='captcha'], input[id*='captcha']"
                                )
                                if input_fields:
                                    input_fields[0].send_keys(solution)
                                    return True
                    
                    # Handle reCAPTCHA
                    elif "recaptcha" in selector:
                        site_key = driver.execute_script(
                            "return window.___grecaptcha_cfg.clients[0].sitekey"
                        )
                        if site_key:
                            solution = self.captcha_solver.solve_recaptcha(
                                driver.current_url, site_key
                            )
                            if solution:
                                driver.execute_script(
                                    f"document.getElementById('g-recaptcha-response').innerHTML='{solution}';"
                                )
                                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {e}")
            return False
    
    async def _handle_captcha_playwright(self, page: Page) -> bool:
        """Handle CAPTCHA using Playwright"""
        if not self.captcha_solver:
            return False
        
        try:
            # Similar logic to Selenium but using Playwright API
            captcha_selectors = [
                "img[src*='captcha']",
                ".captcha",
                "#captcha",
                ".g-recaptcha",
                ".h-captcha"
            ]
            
            for selector in captcha_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    logger.info(f"CAPTCHA detected: {selector}")
                    
                    if "img" in selector:
                        img_src = await elements[0].get_attribute("src")
                        if img_src:
                            solution = self.captcha_solver.solve_image_captcha(img_src)
                            if solution:
                                input_field = await page.query_selector(
                                    "input[name*='captcha'], input[id*='captcha']"
                                )
                                if input_field:
                                    await input_field.fill(solution)
                                    return True
                    
                    elif "recaptcha" in selector:
                        site_key = await page.evaluate(
                            "() => window.___grecaptcha_cfg.clients[0].sitekey"
                        )
                        if site_key:
                            solution = self.captcha_solver.solve_recaptcha(
                                page.url, site_key
                            )
                            if solution:
                                await page.evaluate(
                                    f"document.getElementById('g-recaptcha-response').innerHTML='{solution}';"
                                )
                                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {e}")
            return False
    
    def scrape_sync(
        self, 
        url: str,
        wait_for: Optional[str] = None,
        wait_timeout: int = 10,
        execute_script: Optional[str] = None,
        handle_captcha: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Scrape using Selenium WebDriver"""
        
        if not self._driver:
            self._driver = self._setup_selenium_driver()
        
        try:
            # Navigate to URL
            self._driver.get(url)
            
            # Wait for specific element if specified
            if wait_for:
                if not self._wait_for_element(self._driver, wait_for, timeout=wait_timeout):
                    logger.warning(f"Element {wait_for} not found within {wait_timeout}s")
            
            # Handle CAPTCHA if present
            if handle_captcha:
                self._handle_captcha_selenium(self._driver)
            
            # Execute custom JavaScript if provided
            if execute_script:
                self._driver.execute_script(execute_script)
            
            # Get page source and basic info
            page_source = self._driver.page_source
            title = self._driver.title
            current_url = self._driver.current_url
            
            result = {
                'url': current_url,
                'original_url': url,
                'title': title,
                'page_source': page_source,
                'timestamp': time.time()
            }
            
            self.stats['successful_requests'] += 1
            return result
            
        except WebDriverException as e:
            logger.error(f"WebDriver error for {url}: {e}")
            self.stats['failed_requests'] += 1
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    async def scrape_async(
        self, 
        url: str,
        wait_for: Optional[str] = None,
        wait_timeout: int = 10,
        execute_script: Optional[str] = None,
        handle_captcha: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Scrape using Playwright"""
        
        if not self.use_playwright:
            # Fall back to sync method
            return self.scrape_sync(url, wait_for, wait_timeout, execute_script, handle_captcha, **kwargs)
        
        if not self._browser:
            self._browser = await self._setup_playwright_browser()
        
        try:
            page = await self._context.new_page()
            
            # Navigate to URL
            await page.goto(url, timeout=self.config.timeout * 1000)
            
            # Wait for specific element if specified
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=wait_timeout * 1000)
                except Exception:
                    logger.warning(f"Element {wait_for} not found within {wait_timeout}s")
            
            # Handle CAPTCHA if present
            if handle_captcha:
                await self._handle_captcha_playwright(page)
            
            # Execute custom JavaScript if provided
            if execute_script:
                await page.evaluate(execute_script)
            
            # Get page content and basic info
            content = await page.content()
            title = await page.title()
            current_url = page.url
            
            result = {
                'url': current_url,
                'original_url': url,
                'title': title,
                'page_source': content,
                'timestamp': time.time()
            }
            
            await page.close()
            self.stats['successful_requests'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    def fill_form(
        self, 
        form_data: Dict[str, str],
        submit: bool = True,
        submit_selector: str = "input[type='submit'], button[type='submit']"
    ) -> bool:
        """Fill and submit a form using Selenium"""
        
        if not self._driver:
            logger.error("Driver not initialized")
            return False
        
        try:
            for field_name, value in form_data.items():
                # Try different selector strategies
                selectors = [
                    f"input[name='{field_name}']",
                    f"input[id='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"select[name='{field_name}']"
                ]
                
                element_found = False
                for selector in selectors:
                    elements = self._driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        element = elements[0]
                        
                        # Handle different input types
                        tag_name = element.tag_name.lower()
                        input_type = element.get_attribute('type')
                        
                        if tag_name == 'select':
                            # Handle select dropdown
                            from selenium.webdriver.support.ui import Select
                            select = Select(element)
                            try:
                                select.select_by_value(value)
                            except:
                                select.select_by_visible_text(value)
                        elif input_type in ['checkbox', 'radio']:
                            # Handle checkboxes and radio buttons
                            if value.lower() in ['true', '1', 'yes', 'on']:
                                if not element.is_selected():
                                    element.click()
                        else:
                            # Handle text inputs
                            element.clear()
                            element.send_keys(value)
                        
                        element_found = True
                        break
                
                if not element_found:
                    logger.warning(f"Form field '{field_name}' not found")
            
            # Submit form if requested
            if submit:
                submit_elements = self._driver.find_elements(By.CSS_SELECTOR, submit_selector)
                if submit_elements:
                    submit_elements[0].click()
                    return True
                else:
                    logger.warning("Submit button not found")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling form: {e}")
            return False
    
    def close(self):
        """Close browser resources"""
        if self._driver:
            self._driver.quit()
            self._driver = None
        
        if self._browser:
            asyncio.create_task(self._browser.close())
            self._browser = None
        
        if self._playwright:
            asyncio.create_task(self._playwright.stop())
            self._playwright = None
    
    def __del__(self):
        self.close()