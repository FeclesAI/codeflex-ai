"""
Main entry point for the web scraper
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from scrapers.web_scraper import WebScraper
from config.settings import ScrapingConfig, Config


def load_config_from_file(config_file: str) -> ScrapingConfig:
    """Load configuration from JSON file"""
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        return ScrapingConfig(**config_data)
    
    except Exception as e:
        logger.error(f"Error loading config file {config_file}: {e}")
        return ScrapingConfig()


def create_sample_config():
    """Create a sample configuration file"""
    
    sample_config = {
        "base_delay": 1.0,
        "max_delay": 5.0,
        "timeout": 30,
        "max_retries": 3,
        "concurrent_requests": 10,
        "respect_robots_txt": True,
        "headless": True,
        "browser_type": "chrome",
        "output_dir": "output",
        "data_formats": ["json", "csv"],
        "log_level": "INFO"
    }
    
    config_file = "scraper_config.json"
    
    with open(config_file, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"Sample configuration created: {config_file}")


def main():
    """Main function with CLI interface"""
    
    parser = argparse.ArgumentParser(
        description="Comprehensive Web Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url https://example.com --selectors '{"title": "h1", "content": ".content"}'
  python main.py --urls urls.txt --config config.json --browser
  python main.py --sitemap https://example.com/sitemap.xml --max-urls 100
  python main.py --create-config
        """
    )
    
    # Configuration options
    parser.add_argument('--config', help='Configuration file (JSON)')
    parser.add_argument('--create-config', action='store_true', help='Create sample configuration file')
    
    # URL options
    parser.add_argument('--url', help='Single URL to scrape')
    parser.add_argument('--urls', help='File containing URLs to scrape (one per line)')
    parser.add_argument('--sitemap', help='Sitemap URL to scrape')
    
    # Scraping options
    parser.add_argument('--selectors', help='JSON string of CSS selectors for data extraction')
    parser.add_argument('--selectors-file', help='File containing CSS selectors (JSON)')
    parser.add_argument('--browser', action='store_true', help='Use browser automation')
    parser.add_argument('--pagination', action='store_true', help='Follow pagination')
    parser.add_argument('--max-pages', type=int, help='Maximum pages to scrape')
    parser.add_argument('--max-urls', type=int, help='Maximum URLs to scrape')
    
    # Output options
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--format', choices=['json', 'csv', 'excel'], action='append', help='Output format(s)')
    
    # Performance options
    parser.add_argument('--concurrent', type=int, help='Number of concurrent requests')
    parser.add_argument('--delay', type=float, help='Delay between requests (seconds)')
    
    # Browser options
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--browser-type', choices=['chrome', 'firefox', 'safari'], help='Browser type')
    
    # Other options
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--stats', action='store_true', help='Show detailed statistics')
    
    args = parser.parse_args()
    
    # Create sample config if requested
    if args.create_config:
        create_sample_config()
        return
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
    else:
        config = ScrapingConfig()
    
    # Override config with command line arguments
    if args.concurrent:
        config.concurrent_requests = args.concurrent
    if args.delay:
        config.base_delay = args.delay
    if args.output:
        config.output_dir = args.output
    if args.format:
        config.data_formats = args.format
    if args.headless:
        config.headless = True
    if args.browser_type:
        config.browser_type = args.browser_type
    if args.verbose:
        config.log_level = "DEBUG"
    
    # Load selectors
    selectors = None
    if args.selectors:
        try:
            selectors = json.loads(args.selectors)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in selectors: {e}")
            sys.exit(1)
    elif args.selectors_file:
        try:
            with open(args.selectors_file, 'r') as f:
                selectors = json.load(f)
        except Exception as e:
            logger.error(f"Error loading selectors file: {e}")
            sys.exit(1)
    
    # Determine what to scrape
    urls = []
    
    if args.url:
        urls = [args.url]
    elif args.urls:
        try:
            with open(args.urls, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Error loading URLs file: {e}")
            sys.exit(1)
    elif args.sitemap:
        # Will be handled separately
        pass
    else:
        logger.error("No URLs specified. Use --url, --urls, or --sitemap")
        sys.exit(1)
    
    # Start scraping
    with WebScraper(config) as scraper:
        try:
            if args.sitemap:
                # Scrape from sitemap
                results = scraper.scrape_sitemap(
                    args.sitemap,
                    selectors=selectors,
                    max_urls=args.max_urls
                )
            elif args.pagination and len(urls) == 1:
                # Scrape with pagination
                results = scraper.scrape_with_pagination(
                    urls[0],
                    selectors=selectors,
                    max_pages=args.max_pages,
                    use_browser=args.browser
                )
            elif len(urls) == 1:
                # Scrape single URL
                result = scraper.scrape_single_url(
                    urls[0],
                    selectors=selectors,
                    use_browser=args.browser
                )
                results = [result] if result else []
            else:
                # Scrape multiple URLs
                results = scraper.scrape_multiple_urls(
                    urls,
                    selectors=selectors,
                    use_browser=args.browser,
                    max_concurrent=config.concurrent_requests
                )
            
            # Save results
            scraper.save_results()
            
            # Print summary
            print(f"\nScraping completed!")
            print(f"Successfully scraped: {len(results)} pages")
            print(f"Errors: {len(scraper.errors)}")
            
            if args.stats:
                stats = scraper.get_comprehensive_stats()
                print("\nDetailed Statistics:")
                print(json.dumps(stats, indent=2))
            
        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()