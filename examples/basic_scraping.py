"""
Basic web scraping examples
"""
import asyncio
from scrapers.web_scraper import WebScraper
from config.settings import ScrapingConfig


def basic_html_scraping():
    """Example of basic HTML scraping"""
    
    # Configure scraper
    config = ScrapingConfig(
        base_delay=1.0,
        max_retries=3,
        respect_robots_txt=True
    )
    
    # Define selectors for data extraction
    selectors = {
        'title': 'h1',
        'description': {
            'selector': 'meta[name="description"]',
            'attribute': 'attr:content'
        },
        'links': {
            'selector': 'a[href]',
            'attribute': 'attr:href',
            'multiple': True
        },
        'price': {
            'selector': '.price',
            'transform': lambda x: float(x.replace('$', '').replace(',', '')) if x else 0
        }
    }
    
    with WebScraper(config) as scraper:
        # Scrape single URL
        result = scraper.scrape_single_url(
            'https://example.com/product/123',
            selectors=selectors
        )
        
        if result:
            print("Scraped data:", result['data'])
        
        # Save results
        scraper.save_results(formats=['json', 'csv'])
        
        # Print statistics
        stats = scraper.get_comprehensive_stats()
        print("Scraping stats:", stats)


def multiple_urls_scraping():
    """Example of scraping multiple URLs"""
    
    config = ScrapingConfig(
        concurrent_requests=5,
        base_delay=0.5
    )
    
    urls = [
        'https://example.com/page1',
        'https://example.com/page2',
        'https://example.com/page3'
    ]
    
    selectors = {
        'title': 'h1',
        'content': '.content'
    }
    
    with WebScraper(config) as scraper:
        results = scraper.scrape_multiple_urls(
            urls,
            selectors=selectors,
            max_concurrent=3
        )
        
        print(f"Scraped {len(results)} pages")
        scraper.save_results()


async def async_scraping_example():
    """Example of asynchronous scraping"""
    
    config = ScrapingConfig(
        concurrent_requests=10,
        base_delay=0.2
    )
    
    urls = [f'https://example.com/page{i}' for i in range(1, 21)]
    
    selectors = {
        'title': 'h1',
        'links': {
            'selector': 'a[href]',
            'attribute': 'attr:href',
            'multiple': True
        }
    }
    
    scraper = WebScraper(config)
    
    try:
        results = await scraper.scrape_multiple_urls_async(
            urls,
            selectors=selectors,
            max_concurrent=5
        )
        
        print(f"Scraped {len(results)} pages asynchronously")
        scraper.save_results()
        
    finally:
        scraper.close()


def pagination_scraping_example():
    """Example of scraping with pagination"""
    
    config = ScrapingConfig(
        base_delay=2.0,
        respect_robots_txt=True
    )
    
    selectors = {
        'articles': {
            'selector': '.article',
            'multiple': True
        },
        'title': 'h2',
        'summary': '.summary'
    }
    
    with WebScraper(config) as scraper:
        results = scraper.scrape_with_pagination(
            'https://example.com/blog',
            selectors=selectors,
            max_pages=5
        )
        
        print(f"Scraped {len(results)} pages with pagination")
        scraper.save_results()


if __name__ == "__main__":
    print("Running basic HTML scraping example...")
    basic_html_scraping()
    
    print("\nRunning multiple URLs scraping example...")
    multiple_urls_scraping()
    
    print("\nRunning pagination scraping example...")
    pagination_scraping_example()
    
    print("\nRunning async scraping example...")
    asyncio.run(async_scraping_example())