"""
Browser-based scraping examples using Selenium/Playwright
"""
import time
from scrapers.web_scraper import WebScraper
from config.settings import ScrapingConfig


def javascript_heavy_site_scraping():
    """Example of scraping JavaScript-heavy sites"""
    
    config = ScrapingConfig(
        headless=True,
        browser_type="chrome",
        timeout=30
    )
    
    selectors = {
        'dynamic_content': '.dynamic-content',
        'loaded_items': {
            'selector': '.item',
            'multiple': True
        }
    }
    
    with WebScraper(config) as scraper:
        # Scrape with browser automation
        result = scraper.scrape_single_url(
            'https://example.com/spa-app',
            selectors=selectors,
            use_browser=True,
            wait_for='.dynamic-content',  # Wait for this element to load
            wait_timeout=10
        )
        
        if result:
            print("Scraped dynamic content:", result['data'])
        
        scraper.save_results()


def form_submission_example():
    """Example of form filling and submission"""
    
    config = ScrapingConfig(
        headless=False,  # Show browser for demonstration
        browser_type="chrome"
    )
    
    form_data = {
        'username': 'test_user',
        'password': 'test_password',
        'email': 'test@example.com',
        'newsletter': 'true'
    }
    
    with WebScraper(config) as scraper:
        result = scraper.fill_and_submit_form(
            'https://example.com/register',
            form_data=form_data,
            submit=True,
            wait_after_submit=3.0
        )
        
        if result:
            print("Form submitted successfully")
            print("Result page URL:", result['url'])
        
        scraper.save_results()


def infinite_scroll_scraping():
    """Example of scraping infinite scroll pages"""
    
    config = ScrapingConfig(
        headless=True,
        browser_type="chrome"
    )
    
    selectors = {
        'posts': {
            'selector': '.post',
            'multiple': True
        },
        'post_title': 'h3',
        'post_content': '.content'
    }
    
    # JavaScript to scroll and load more content
    scroll_script = """
    // Scroll to bottom multiple times to load more content
    for (let i = 0; i < 5; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    """
    
    with WebScraper(config) as scraper:
        result = scraper.scrape_single_url(
            'https://example.com/infinite-scroll',
            selectors=selectors,
            use_browser=True,
            execute_script=scroll_script
        )
        
        if result:
            print(f"Scraped {len(result['data']['posts'])} posts")
        
        scraper.save_results()


def captcha_handling_example():
    """Example of handling CAPTCHAs (requires CAPTCHA service)"""
    
    config = ScrapingConfig(
        headless=True,
        browser_type="chrome",
        captcha_service="2captcha",  # or "anticaptcha"
        captcha_api_key="your_api_key_here"
    )
    
    selectors = {
        'protected_content': '.protected-content'
    }
    
    with WebScraper(config) as scraper:
        result = scraper.scrape_single_url(
            'https://example.com/captcha-protected',
            selectors=selectors,
            use_browser=True,
            handle_captcha=True
        )
        
        if result:
            print("Successfully bypassed CAPTCHA and scraped content")
        
        scraper.save_results()


def multi_step_interaction():
    """Example of multi-step browser interaction"""
    
    config = ScrapingConfig(
        headless=False,
        browser_type="chrome"
    )
    
    with WebScraper(config) as scraper:
        # Step 1: Navigate to login page
        scraper.scrape_single_url(
            'https://example.com/login',
            use_browser=True
        )
        
        # Step 2: Fill login form
        login_data = {
            'username': 'your_username',
            'password': 'your_password'
        }
        
        scraper.browser_scraper.fill_form(login_data, submit=True)
        time.sleep(3)  # Wait for login to complete
        
        # Step 3: Navigate to protected area and scrape
        selectors = {
            'user_data': '.user-profile',
            'dashboard_items': {
                'selector': '.dashboard-item',
                'multiple': True
            }
        }
        
        result = scraper.scrape_single_url(
            'https://example.com/dashboard',
            selectors=selectors,
            use_browser=True
        )
        
        if result:
            print("Successfully scraped protected content after login")
        
        scraper.save_results()


if __name__ == "__main__":
    print("Running JavaScript-heavy site scraping example...")
    javascript_heavy_site_scraping()
    
    print("\nRunning form submission example...")
    form_submission_example()
    
    print("\nRunning infinite scroll scraping example...")
    infinite_scroll_scraping()
    
    print("\nRunning multi-step interaction example...")
    multi_step_interaction()
    
    # Uncomment if you have CAPTCHA service configured
    # print("\nRunning CAPTCHA handling example...")
    # captcha_handling_example()