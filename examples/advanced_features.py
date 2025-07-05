"""
Advanced scraping features examples
"""
import schedule
import time
from datetime import datetime
from scrapers.web_scraper import WebScraper
from config.settings import ScrapingConfig


def proxy_rotation_example():
    """Example using proxy rotation"""
    
    # List of proxy servers (replace with real proxies)
    proxy_list = [
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080',
        'http://proxy3.example.com:8080'
    ]
    
    config = ScrapingConfig(
        use_proxies=True,
        proxy_list=proxy_list,
        proxy_rotation=True,
        base_delay=2.0
    )
    
    urls = [f'https://httpbin.org/ip' for _ in range(5)]  # Test IP endpoint
    
    with WebScraper(config) as scraper:
        results = scraper.scrape_multiple_urls(urls)
        
        # Check if different IPs were used
        for i, result in enumerate(results):
            print(f"Request {i+1}: {result.get('data', {})}")
        
        # Print proxy statistics
        if scraper.html_scraper.proxy_manager:
            proxy_stats = scraper.html_scraper.proxy_manager.get_proxy_stats()
            print("Proxy statistics:", proxy_stats)


def data_validation_example():
    """Example with data validation"""
    
    # Define validation schema
    validation_schema = {
        'title': {'type': 'string', 'required': True, 'minlength': 1},
        'price': {'type': 'number', 'required': True, 'min': 0},
        'description': {'type': 'string', 'required': False},
        'in_stock': {'type': 'boolean', 'required': True}
    }
    
    selectors = {
        'title': 'h1',
        'price': {
            'selector': '.price',
            'transform': lambda x: float(x.replace('$', '').replace(',', '')) if x else 0
        },
        'description': '.description',
        'in_stock': {
            'selector': '.stock-status',
            'transform': lambda x: 'in stock' in x.lower() if x else False
        }
    }
    
    config = ScrapingConfig()
    
    with WebScraper(config) as scraper:
        result = scraper.scrape_single_url(
            'https://example.com/product',
            selectors=selectors
        )
        
        if result and 'data' in result:
            # Validate extracted data
            validation_result = scraper.data_processor.validate_data(
                result['data'], 
                validation_schema
            )
            
            if validation_result['valid']:
                print("Data validation passed")
                scraper.results.append(result)
            else:
                print("Data validation failed:", validation_result['errors'])
        
        scraper.save_results()


def duplicate_detection_example():
    """Example with duplicate detection"""
    
    urls = [
        'https://example.com/page1',
        'https://example.com/page1',  # Duplicate
        'https://example.com/page2',
        'https://example.com/page1',  # Another duplicate
    ]
    
    selectors = {
        'content': '.main-content'
    }
    
    config = ScrapingConfig()
    
    with WebScraper(config) as scraper:
        for url in urls:
            result = scraper.scrape_single_url(url, selectors=selectors)
            print(f"Scraped {url}: {'Success' if result else 'Failed'}")
        
        # Print duplicate statistics
        duplicate_stats = scraper.data_processor.get_duplicate_stats()
        print("Duplicate detection stats:", duplicate_stats)
        
        scraper.save_results()


def scheduled_scraping_example():
    """Example of scheduled scraping"""
    
    def scraping_job():
        """Job function for scheduled scraping"""
        print(f"Starting scheduled scraping at {datetime.now()}")
        
        config = ScrapingConfig(
            base_delay=1.0,
            output_dir=f"output/scheduled_{datetime.now().strftime('%Y%m%d')}"
        )
        
        selectors = {
            'headlines': {
                'selector': '.headline',
                'multiple': True
            },
            'timestamp': {
                'selector': '.timestamp',
                'multiple': True
            }
        }
        
        with WebScraper(config) as scraper:
            result = scraper.scrape_single_url(
                'https://example.com/news',
                selectors=selectors
            )
            
            if result:
                print(f"Scraped {len(result['data']['headlines'])} headlines")
            
            scraper.save_results()
            
            # Print statistics
            stats = scraper.get_comprehensive_stats()
            print(f"Scraping completed. Success rate: {stats['html_scraper']['success_rate']:.2%}")
    
    # Schedule the job
    schedule.every(30).minutes.do(scraping_job)  # Every 30 minutes
    schedule.every().hour.do(scraping_job)       # Every hour
    schedule.every().day.at("09:00").do(scraping_job)  # Daily at 9 AM
    
    print("Scheduled scraping jobs configured. Running scheduler...")
    
    # Run scheduler (in production, this would run continuously)
    for _ in range(3):  # Run for 3 iterations as example
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def sitemap_scraping_example():
    """Example of scraping from sitemap"""
    
    config = ScrapingConfig(
        concurrent_requests=5,
        base_delay=1.0
    )
    
    selectors = {
        'title': 'h1',
        'content': '.content',
        'meta_description': {
            'selector': 'meta[name="description"]',
            'attribute': 'attr:content'
        }
    }
    
    # URL filter to only scrape blog posts
    def blog_filter(url):
        return '/blog/' in url and url.endswith('.html')
    
    with WebScraper(config) as scraper:
        results = scraper.scrape_sitemap(
            'https://example.com/sitemap.xml',
            selectors=selectors,
            url_filter=blog_filter,
            max_urls=50
        )
        
        print(f"Scraped {len(results)} pages from sitemap")
        scraper.save_results()


def monitoring_and_metrics_example():
    """Example with monitoring and metrics"""
    
    config = ScrapingConfig(
        enable_metrics=True,
        metrics_port=8000,
        log_level="DEBUG"
    )
    
    urls = [f'https://httpbin.org/delay/{i}' for i in range(1, 6)]
    
    with WebScraper(config) as scraper:
        start_time = time.time()
        
        results = scraper.scrape_multiple_urls(urls, max_concurrent=3)
        
        end_time = time.time()
        
        # Print comprehensive statistics
        stats = scraper.get_comprehensive_stats()
        
        print("=== SCRAPING METRICS ===")
        print(f"Total runtime: {end_time - start_time:.2f} seconds")
        print(f"URLs processed: {stats['total_processed']}")
        print(f"Success rate: {stats['html_scraper']['success_rate']:.2%}")
        print(f"Requests per second: {stats['html_scraper']['requests_per_second']:.2f}")
        print(f"Duplicates found: {stats['duplicate_detection']['duplicates_found']}")
        print(f"Duplicate rate: {stats['duplicate_detection']['duplicate_rate']:.2%}")
        
        scraper.save_results()


if __name__ == "__main__":
    print("Running proxy rotation example...")
    proxy_rotation_example()
    
    print("\nRunning data validation example...")
    data_validation_example()
    
    print("\nRunning duplicate detection example...")
    duplicate_detection_example()
    
    print("\nRunning sitemap scraping example...")
    sitemap_scraping_example()
    
    print("\nRunning monitoring and metrics example...")
    monitoring_and_metrics_example()
    
    # Uncomment to run scheduled scraping (will run for a few minutes)
    # print("\nRunning scheduled scraping example...")
    # scheduled_scraping_example()