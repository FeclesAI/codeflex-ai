# Comprehensive Web Scraper

A powerful, production-ready web scraping framework built with Python that handles dynamic content, pagination, rate limiting, and much more.

## Features

### Core Scraping Capabilities
- **HTML Parsing**: BeautifulSoup integration with CSS selectors and XPath support
- **JavaScript Support**: Selenium and Playwright for dynamic content
- **Concurrent Scraping**: Asynchronous requests with configurable concurrency
- **Rate Limiting**: Respect robots.txt and implement custom delays
- **Session Management**: Persistent sessions with connection pooling

### Advanced Features
- **Proxy Support**: Automatic proxy rotation and management
- **CAPTCHA Handling**: Integration with 2captcha and AntiCaptcha services
- **Form Submission**: Automated form filling and submission
- **Pagination**: Automatic pagination detection and handling
- **Data Processing**: Built-in data cleaning, validation, and duplicate detection
- **Multiple Export Formats**: JSON, CSV, Excel output support

### Monitoring & Reliability
- **Comprehensive Logging**: Structured logging with rotation
- **Error Handling**: Robust error handling and retry mechanisms
- **Statistics**: Detailed scraping metrics and performance monitoring
- **Scheduled Tasks**: Built-in support for scheduled scraping

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd web-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install browser drivers (for Selenium):
```bash
# Chrome
pip install chromedriver-autoinstaller

# Firefox
pip install geckodriver-autoinstaller
```

4. Install Playwright browsers (optional):
```bash
playwright install
```

## Quick Start

### Basic HTML Scraping

```python
from scrapers.web_scraper import WebScraper
from config.settings import ScrapingConfig

# Configure scraper
config = ScrapingConfig(
    base_delay=1.0,
    concurrent_requests=5,
    respect_robots_txt=True
)

# Define data extraction rules
selectors = {
    'title': 'h1',
    'price': {
        'selector': '.price',
        'transform': lambda x: float(x.replace('$', '')) if x else 0
    },
    'description': '.description',
    'images': {
        'selector': 'img[src]',
        'attribute': 'attr:src',
        'multiple': True
    }
}

# Scrape data
with WebScraper(config) as scraper:
    result = scraper.scrape_single_url(
        'https://example.com/product',
        selectors=selectors
    )
    
    if result:
        print("Scraped data:", result['data'])
    
    # Save results
    scraper.save_results(formats=['json', 'csv'])
```

### Browser Automation

```python
# Scrape JavaScript-heavy sites
with WebScraper(config) as scraper:
    result = scraper.scrape_single_url(
        'https://spa-example.com',
        selectors=selectors,
        use_browser=True,
        wait_for='.dynamic-content',
        wait_timeout=10
    )
```

### Multiple URLs with Concurrency

```python
urls = ['https://example.com/page1', 'https://example.com/page2']

with WebScraper(config) as scraper:
    results = scraper.scrape_multiple_urls(
        urls,
        selectors=selectors,
        max_concurrent=5
    )
    
    print(f"Scraped {len(results)} pages")
```

### Pagination Handling

```python
with WebScraper(config) as scraper:
    results = scraper.scrape_with_pagination(
        'https://example.com/blog',
        selectors=selectors,
        max_pages=10
    )
```

## Command Line Interface

The scraper includes a comprehensive CLI:

```bash
# Scrape a single URL
python main.py --url https://example.com --selectors '{"title": "h1"}'

# Scrape multiple URLs from file
python main.py --urls urls.txt --browser --concurrent 5

# Scrape from sitemap
python main.py --sitemap https://example.com/sitemap.xml --max-urls 100

# Use configuration file
python main.py --config config.json --url https://example.com

# Create sample configuration
python main.py --create-config
```

## Configuration

Create a configuration file or use the ScrapingConfig class:

```json
{
  "base_delay": 1.0,
  "max_delay": 5.0,
  "timeout": 30,
  "max_retries": 3,
  "concurrent_requests": 10,
  "respect_robots_txt": true,
  "headless": true,
  "browser_type": "chrome",
  "use_proxies": false,
  "proxy_list": [],
  "output_dir": "output",
  "data_formats": ["json", "csv"],
  "log_level": "INFO"
}
```

## Advanced Usage

### Proxy Rotation

```python
config = ScrapingConfig(
    use_proxies=True,
    proxy_list=[
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080'
    ],
    proxy_rotation=True
)
```

### CAPTCHA Solving

```python
config = ScrapingConfig(
    captcha_service="2captcha",
    captcha_api_key="your_api_key"
)

# CAPTCHA will be automatically detected and solved
result = scraper.scrape_single_url(
    'https://captcha-protected-site.com',
    use_browser=True,
    handle_captcha=True
)
```

### Form Submission

```python
form_data = {
    'username': 'user@example.com',
    'password': 'password123',
    'remember_me': 'true'
}

result = scraper.fill_and_submit_form(
    'https://example.com/login',
    form_data=form_data,
    submit=True
)
```

### Data Validation

```python
# Define validation schema
schema = {
    'title': {'type': 'string', 'required': True},
    'price': {'type': 'number', 'min': 0},
    'in_stock': {'type': 'boolean'}
}

# Validate extracted data
validation_result = scraper.data_processor.validate_data(data, schema)
```

### Scheduled Scraping

```python
import schedule

def scraping_job():
    with WebScraper(config) as scraper:
        results = scraper.scrape_multiple_urls(urls, selectors=selectors)
        scraper.save_results()

# Schedule jobs
schedule.every(30).minutes.do(scraping_job)
schedule.every().day.at("09:00").do(scraping_job)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Data Processing

The scraper includes powerful data processing capabilities:

```python
# Clean text data
clean_text = scraper.data_processor.clean_text(raw_text)

# Extract structured data
emails = scraper.data_processor.extract_emails(text)
phones = scraper.data_processor.extract_phones(text)
numbers = scraper.data_processor.extract_numbers(text)

# Duplicate detection
is_duplicate = scraper.data_processor.is_duplicate(data)

# Export to various formats
scraper.data_processor.save_to_json(data, 'output.json')
scraper.data_processor.save_to_csv(data, 'output.csv')
scraper.data_processor.save_to_excel(data, 'output.xlsx')
```

## Monitoring and Statistics

```python
# Get comprehensive statistics
stats = scraper.get_comprehensive_stats()

print(f"Success rate: {stats['html_scraper']['success_rate']:.2%}")
print(f"Requests per second: {stats['html_scraper']['requests_per_second']:.2f}")
print(f"Duplicates found: {stats['duplicate_detection']['duplicates_found']}")
```

## Error Handling

The scraper includes robust error handling:

- Automatic retries with exponential backoff
- Graceful handling of network timeouts
- Proxy failure detection and rotation
- Comprehensive error logging
- Recovery from browser crashes

## Best Practices

1. **Respect robots.txt**: Always enable `respect_robots_txt=True`
2. **Use appropriate delays**: Set reasonable delays between requests
3. **Monitor your scraping**: Use the built-in statistics and logging
4. **Handle errors gracefully**: Check return values and handle exceptions
5. **Use proxies responsibly**: Rotate proxies and respect rate limits
6. **Validate your data**: Use the built-in validation features
7. **Clean up resources**: Use context managers or call `close()` explicitly

## Legal and Ethical Considerations

- Always check and respect robots.txt
- Don't overload servers with too many concurrent requests
- Respect rate limits and implement appropriate delays
- Be aware of terms of service and legal restrictions
- Consider the impact of your scraping on the target website
- Use the scraped data responsibly and ethically

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.