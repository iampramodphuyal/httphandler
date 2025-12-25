# HTTP Client Usage Guide

This guide covers common use cases for the HTTP client package, designed for web scraping with support for both synchronous and asynchronous operations.

---

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Async Usage](#async-usage)
3. [Batch Operations](#batch-operations)
4. [Speed vs Stealth Modes](#speed-vs-stealth-modes)
5. [Cookie Management](#cookie-management)
6. [Proxy Rotation](#proxy-rotation)
7. [Rate Limiting](#rate-limiting)
8. [Error Handling and Retries](#error-handling-and-retries)
9. [Browser Fingerprinting](#browser-fingerprinting)
10. [Real-World Examples](#real-world-examples)

---

## Basic Usage

### Simple GET Request

```python
from http_client import ScraperClient

# Create a client
client = ScraperClient()

# Make a GET request
response = client.get("https://httpbin.org/get")

print(f"Status: {response.status_code}")
print(f"Body: {response.text}")

# Always close when done
client.close()
```

### Using Context Manager (Recommended)

```python
from http_client import ScraperClient

with ScraperClient() as client:
    response = client.get("https://httpbin.org/get")
    print(response.json())
# Client automatically closed
```

### POST Request with JSON

```python
from http_client import ScraperClient

with ScraperClient() as client:
    response = client.post(
        "https://httpbin.org/post",
        json={"username": "user", "action": "login"}
    )
    print(response.json())
```

### POST Request with Form Data

```python
from http_client import ScraperClient

with ScraperClient() as client:
    response = client.post(
        "https://httpbin.org/post",
        data={"field1": "value1", "field2": "value2"}
    )
    print(response.json())
```

### Request with Custom Headers

```python
from http_client import ScraperClient

with ScraperClient() as client:
    response = client.get(
        "https://httpbin.org/headers",
        headers={
            "Authorization": "Bearer my-token",
            "X-Custom-Header": "custom-value"
        }
    )
    print(response.json())
```

### Request with Query Parameters

```python
from http_client import ScraperClient

with ScraperClient() as client:
    response = client.get(
        "https://httpbin.org/get",
        params={"search": "python", "page": "1", "limit": "10"}
    )
    # URL becomes: https://httpbin.org/get?search=python&page=1&limit=10
    print(response.json())
```

---

## Async Usage

### Simple Async Request

```python
import asyncio
from http_client import ScraperClient

async def main():
    async with ScraperClient() as client:
        response = await client.get_async("https://httpbin.org/get")
        print(response.json())

asyncio.run(main())
```

### Multiple Async Requests

```python
import asyncio
from http_client import ScraperClient

async def fetch_page(client, url):
    response = await client.get_async(url)
    return response.json()

async def main():
    async with ScraperClient() as client:
        # Run multiple requests concurrently
        results = await asyncio.gather(
            fetch_page(client, "https://httpbin.org/get?id=1"),
            fetch_page(client, "https://httpbin.org/get?id=2"),
            fetch_page(client, "https://httpbin.org/get?id=3"),
        )
        for result in results:
            print(result)

asyncio.run(main())
```

---

## Batch Operations

### Batch GET with Thread Pool (Sync)

Use `gather_sync()` for scraping multiple URLs using a thread pool:

```python
from http_client import ScraperClient

urls = [
    "https://httpbin.org/get?page=1",
    "https://httpbin.org/get?page=2",
    "https://httpbin.org/get?page=3",
    "https://httpbin.org/get?page=4",
    "https://httpbin.org/get?page=5",
]

with ScraperClient(max_workers=5) as client:
    results = client.gather_sync(urls)

    print(f"Successful: {results.success_count}")
    print(f"Failed: {results.failure_count}")

    for i, response in enumerate(results.responses):
        if response:
            print(f"URL {i}: Status {response.status_code}")

    # Check for errors
    for idx, error in results.errors.items():
        print(f"URL {idx} failed: {error}")
```

### Batch GET with Asyncio (Async)

Use `gather_async()` for high-concurrency scraping:

```python
import asyncio
from http_client import ScraperClient

async def main():
    urls = [f"https://httpbin.org/get?page={i}" for i in range(100)]

    async with ScraperClient() as client:
        # Limit concurrency to 20 simultaneous requests
        results = await client.gather_async(urls, concurrency=20)

        print(f"Successful: {results.success_count}")
        print(f"Failed: {results.failure_count}")

        if results.all_succeeded:
            print("All requests completed successfully!")

asyncio.run(main())
```

### Batch with Custom Requests

```python
from http_client import ScraperClient, Request

requests = [
    Request(method="GET", url="https://httpbin.org/get"),
    Request(method="POST", url="https://httpbin.org/post", json={"id": 1}),
    Request(method="POST", url="https://httpbin.org/post", json={"id": 2}),
]

with ScraperClient() as client:
    results = client.gather_sync(requests)

    for response in results.responses:
        if response:
            print(response.json())
```

### Stop on First Error

```python
from http_client import ScraperClient

urls = ["https://httpbin.org/get", "https://invalid.url", "https://httpbin.org/get"]

with ScraperClient() as client:
    results = client.gather_sync(urls, stop_on_error=True)

    # Processing stops after the first error
    print(f"Completed: {results.success_count + results.failure_count}")
```

---

## Speed vs Stealth Modes

### Speed Mode (Default)

Optimized for maximum throughput with minimal overhead:

```python
from http_client import ScraperClient

client = ScraperClient(
    mode="speed",
    rate_limit=0,        # No rate limiting
    retries=1,           # Minimal retries
    max_workers=50,      # High thread pool
)

# Fast scraping without fingerprinting or delays
with client:
    results = client.gather_sync(urls)
```

**Speed mode characteristics:**
- No artificial delays between requests
- Minimal headers (no browser fingerprinting)
- No TLS fingerprint impersonation
- Maximum connection pooling
- Best for APIs and non-protected sites

### Stealth Mode

Mimics real browser behavior to avoid detection:

```python
from http_client import ScraperClient

client = ScraperClient(
    mode="stealth",
    profile="chrome_120",     # Browser fingerprint
    persist_cookies=True,     # Maintain session
    rate_limit=2.0,           # 2 requests/sec per domain
    min_delay=1.0,            # Random delay 1-3 seconds
    max_delay=3.0,
)

with client:
    # First request establishes session
    response = client.get("https://example.com")

    # Subsequent requests include cookies and realistic timing
    response = client.get("https://example.com/page2")
```

**Stealth mode characteristics:**
- Random delays between requests (1-3 seconds by default)
- Full browser-like headers with correct ordering
- TLS fingerprint matches real browsers
- Automatic referer chain building
- Cookie persistence across requests
- Best for protected sites with anti-bot measures

---

## Cookie Management

### Default: Stateless (No Persistence)

By default, cookies are NOT persisted between requests:

```python
from http_client import ScraperClient

with ScraperClient() as client:
    # Response contains cookies but they're not stored
    response = client.get("https://httpbin.org/cookies/set?session=abc123")
    print(f"Response cookies: {response.cookies}")

    # Next request does NOT include previous cookies
    response = client.get("https://httpbin.org/cookies")
    print(f"Sent cookies: {response.json()}")  # Empty
```

### Enable Cookie Persistence

```python
from http_client import ScraperClient

with ScraperClient(persist_cookies=True) as client:
    # First request sets cookies
    client.get("https://httpbin.org/cookies/set?session=abc123&user=john")

    # Subsequent requests automatically include cookies
    response = client.get("https://httpbin.org/cookies")
    print(f"Sent cookies: {response.json()}")  # Contains session and user
```

### Manual Cookie Injection

```python
from http_client import ScraperClient

with ScraperClient() as client:
    # Send specific cookies with request
    response = client.get(
        "https://httpbin.org/cookies",
        cookies={"auth_token": "secret123", "user_id": "42"}
    )
    print(response.json())
```

### Accessing the Cookie Store

```python
from http_client import ScraperClient

with ScraperClient(persist_cookies=True) as client:
    client.get("https://httpbin.org/cookies/set?token=xyz")

    # Access cookie store directly
    if client.cookie_store:
        # Get all cookies
        all_cookies = client.cookie_store.get_all()
        print(f"All cookies: {all_cookies}")

        # Get cookies for specific URL
        url_cookies = client.cookie_store.get_for_url("https://httpbin.org/path")
        print(f"URL cookies: {url_cookies}")

        # Clear all cookies
        client.cookie_store.clear_all()
```

---

## Proxy Rotation

### Basic Proxy Usage

```python
from http_client import ScraperClient

with ScraperClient() as client:
    # Single request with specific proxy
    response = client.get(
        "https://httpbin.org/ip",
        proxy="http://proxy.example.com:8080"
    )
    print(response.json())
```

### Proxy Pool with Round-Robin

```python
from http_client import ScraperClient

client = ScraperClient(
    proxies=[
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        "http://proxy3.example.com:8080",
    ],
    proxy_strategy="round_robin",  # Cycle through proxies
)

with client:
    # Each request uses next proxy in rotation
    for i in range(6):
        response = client.get("https://httpbin.org/ip")
        print(f"Request {i}: {response.json()['origin']}")
```

### Proxy Pool with Random Selection

```python
from http_client import ScraperClient

client = ScraperClient(
    proxies=[
        "http://proxy1:8080",
        "http://proxy2:8080",
        "http://proxy3:8080",
    ],
    proxy_strategy="random",  # Random proxy each request
)
```

### Proxy Pool with Least-Recently-Used

```python
from http_client import ScraperClient

client = ScraperClient(
    proxies=[
        "http://proxy1:8080",
        "http://proxy2:8080",
        "http://proxy3:8080",
    ],
    proxy_strategy="least_used",  # Use least recently used proxy
)
```

### Proxy with Authentication

```python
from http_client import ScraperClient

client = ScraperClient(
    proxies=[
        "http://username:password@proxy.example.com:8080",
        "socks5://user:pass@socks-proxy.example.com:1080",
    ],
)
```

### Proxy Health Tracking

```python
from http_client import ScraperClient

client = ScraperClient(
    proxies=["http://proxy1:8080", "http://proxy2:8080"],
    proxy_max_failures=3,    # Disable after 3 consecutive failures
    proxy_cooldown=300.0,    # Re-enable after 5 minutes
)

with client:
    # Make requests...

    # Check proxy pool status
    if client.proxy_pool:
        stats = client.proxy_pool.get_stats()
        print(f"Available proxies: {stats['available']}/{stats['total']}")

        for proxy in stats['proxies']:
            print(f"  {proxy['url']}: enabled={proxy['enabled']}, "
                  f"failures={proxy['consecutive_failures']}")
```

---

## Rate Limiting

### Per-Domain Rate Limiting

```python
from http_client import ScraperClient

# 2 requests per second per domain (default)
client = ScraperClient(rate_limit=2.0)

with client:
    # These will be rate-limited to 2/sec for example.com
    for i in range(10):
        client.get(f"https://example.com/page/{i}")
```

### Disable Rate Limiting

```python
from http_client import ScraperClient

client = ScraperClient(rate_limit=0)  # No rate limiting
```

### Custom Domain Rates

```python
from http_client import ScraperClient

client = ScraperClient(rate_limit=1.0)  # Default: 1 req/sec

with client:
    # Set higher rate for specific API
    if client.rate_limiter:
        client.rate_limiter.set_domain_rate("api.example.com", 10.0)
        client.rate_limiter.set_domain_rate("slow.example.com", 0.5)
```

---

## Error Handling and Retries

### Basic Error Handling

```python
from http_client import (
    ScraperClient,
    TransportError,
    HTTPError,
    MaxRetriesExceeded,
)

with ScraperClient() as client:
    try:
        response = client.get("https://example.com")
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx
        print(response.text)
    except TransportError as e:
        print(f"Connection failed: {e}")
    except HTTPError as e:
        print(f"HTTP error {e.response.status_code}: {e}")
    except MaxRetriesExceeded as e:
        print(f"All retries failed for {e.url}")
```

### Configure Retries

```python
from http_client import ScraperClient

client = ScraperClient(
    retries=5,                    # Retry up to 5 times
    retry_codes=(429, 500, 502, 503, 504),  # Retry on these status codes
    retry_backoff_base=2.0,       # Exponential backoff: 1s, 2s, 4s, 8s, 16s
)
```

### Batch Error Handling

```python
from http_client import ScraperClient

urls = [
    "https://httpbin.org/get",
    "https://httpbin.org/status/500",  # Will fail
    "https://httpbin.org/get",
]

with ScraperClient(retries=0) as client:
    results = client.gather_sync(urls)

    # Process successful responses
    for i, response in enumerate(results.responses):
        if response:
            print(f"URL {i}: Success ({response.status_code})")

    # Handle errors
    for idx, error in results.errors.items():
        print(f"URL {idx}: Failed - {error}")

    # Raise first error if needed
    if not results.all_succeeded:
        results.raise_on_error()
```

---

## Browser Fingerprinting

### Available Browser Profiles

```python
from http_client import PROFILES, get_profile

# List all available profiles
print("Available profiles:")
for name in sorted(PROFILES.keys()):
    profile = PROFILES[name]
    print(f"  {name}: {profile.impersonate}")

# Profiles include:
# - chrome_120, chrome_119, chrome_118
# - firefox_121, firefox_120, firefox_117
# - safari_17, safari_16, safari_15
# - edge_120, edge_119
```

### Using Specific Profile

```python
from http_client import ScraperClient

# Use Firefox fingerprint
client = ScraperClient(
    mode="stealth",
    profile="firefox_121",
)

with client:
    response = client.get("https://httpbin.org/headers")
    print(response.json())  # Shows Firefox-like headers
```

### Profile Details

```python
from http_client import get_profile

profile = get_profile("chrome_120")

print(f"Name: {profile.name}")
print(f"Impersonate: {profile.impersonate}")
print(f"User-Agent: {profile.user_agent}")
print(f"Header Order: {profile.header_order}")
print(f"Sec-CH-UA: {profile.sec_ch_ua}")
```

### Custom Header Generation

```python
from http_client import HeaderGenerator

gen = HeaderGenerator("chrome_120")

# Generate headers for a request
headers = gen.generate(
    url="https://example.com/page",
    method="GET",
    custom_headers={"Authorization": "Bearer token"},
)

print(headers)
# Includes: User-Agent, Accept, Sec-Fetch-*, etc.
# In correct browser order
```

---

## Real-World Examples

### Example 1: Scraping a Paginated API

```python
import asyncio
from http_client import ScraperClient

async def scrape_api():
    async with ScraperClient(rate_limit=5.0) as client:
        all_data = []
        page = 1

        while True:
            response = await client.get_async(
                "https://api.example.com/items",
                params={"page": str(page), "limit": "100"}
            )

            if not response.ok:
                break

            data = response.json()
            if not data["items"]:
                break

            all_data.extend(data["items"])
            page += 1

            print(f"Fetched page {page}, total items: {len(all_data)}")

        return all_data

data = asyncio.run(scrape_api())
print(f"Total items scraped: {len(data)}")
```

### Example 2: Login and Session Handling

```python
from http_client import ScraperClient

with ScraperClient(persist_cookies=True, mode="stealth") as client:
    # Step 1: Get login page (may set CSRF token)
    client.get("https://example.com/login")

    # Step 2: Submit login form
    response = client.post(
        "https://example.com/login",
        data={
            "username": "myuser",
            "password": "mypass",
        }
    )

    if response.ok:
        # Step 3: Access protected pages (cookies automatically included)
        dashboard = client.get("https://example.com/dashboard")
        print(dashboard.text)

        profile = client.get("https://example.com/profile")
        print(profile.text)
```

### Example 3: Scraping with Proxy Rotation

```python
from http_client import ScraperClient

proxies = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]

client = ScraperClient(
    mode="stealth",
    proxies=proxies,
    proxy_strategy="round_robin",
    proxy_max_failures=3,
    rate_limit=1.0,
)

with client:
    urls = [f"https://example.com/product/{i}" for i in range(100)]
    results = client.gather_sync(urls)

    for i, response in enumerate(results.responses):
        if response:
            # Process product data
            print(f"Product {i}: {response.status_code}")
```

### Example 4: High-Performance Async Scraping

```python
import asyncio
from http_client import ScraperClient

async def scrape_urls(urls: list[str], concurrency: int = 50):
    async with ScraperClient(
        mode="speed",
        rate_limit=0,
        default_concurrency=concurrency,
    ) as client:
        results = await client.gather_async(urls, concurrency=concurrency)

        successful = [r for r in results.responses if r and r.ok]
        failed = list(results.errors.values())

        return successful, failed

async def main():
    urls = [f"https://httpbin.org/get?id={i}" for i in range(1000)]

    successful, failed = await scrape_urls(urls, concurrency=100)

    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

asyncio.run(main())
```

### Example 5: E-commerce Price Monitoring

```python
import asyncio
from http_client import ScraperClient, Request

async def monitor_prices(product_urls: list[str]):
    client = ScraperClient(
        mode="stealth",
        profile="chrome_120",
        persist_cookies=True,
        rate_limit=1.0,
        min_delay=2.0,
        max_delay=5.0,
    )

    async with client:
        results = await client.gather_async(product_urls, concurrency=5)

        prices = {}
        for i, response in enumerate(results.responses):
            if response and response.ok:
                # Parse price from response (site-specific)
                # prices[product_urls[i]] = parse_price(response.text)
                prices[product_urls[i]] = response.status_code

        return prices

# Usage
urls = [
    "https://shop.example.com/product/1",
    "https://shop.example.com/product/2",
    "https://shop.example.com/product/3",
]

prices = asyncio.run(monitor_prices(urls))
print(prices)
```

### Example 6: API with Authentication

```python
from http_client import ScraperClient

# API with Bearer token
with ScraperClient(
    default_headers={"Authorization": "Bearer your-api-token"}
) as client:
    # All requests include the auth header
    users = client.get("https://api.example.com/users").json()
    posts = client.get("https://api.example.com/posts").json()

    # Override headers for specific request
    admin_data = client.get(
        "https://api.example.com/admin",
        headers={"Authorization": "Bearer admin-token"}
    ).json()
```

---

## Configuration Reference

### All Configuration Options

```python
from http_client import ScraperClient

client = ScraperClient(
    # Mode
    mode="speed",                # "speed" or "stealth"

    # Session
    persist_cookies=False,       # Enable cookie persistence

    # Fingerprinting
    profile="chrome_120",        # Browser profile

    # Rate Limiting
    rate_limit=2.0,              # Requests/second per domain (0 to disable)

    # Timeouts
    timeout=30.0,                # Total request timeout
    connect_timeout=10.0,        # Connection timeout

    # Retries
    retries=3,                   # Retry attempts
    retry_codes=(429, 500, 502, 503, 504, 520, 521, 522, 523, 524),
    retry_backoff_base=2.0,      # Exponential backoff base

    # Proxies
    proxies=None,                # List of proxy URLs
    proxy_strategy="round_robin", # "round_robin", "random", "least_used"
    proxy_max_failures=3,        # Failures before disabling
    proxy_cooldown=300.0,        # Seconds before re-enabling

    # Concurrency
    max_workers=10,              # Thread pool size for gather_sync
    default_concurrency=10,      # Semaphore for gather_async

    # Stealth Mode Delays
    min_delay=1.0,               # Minimum random delay
    max_delay=3.0,               # Maximum random delay

    # SSL/Redirects
    verify_ssl=True,             # Verify SSL certificates
    follow_redirects=True,       # Follow HTTP redirects
    max_redirects=10,            # Maximum redirects

    # Default Headers
    default_headers={},          # Headers for all requests
)
```

---

## Best Practices

1. **Always use context managers** to ensure proper resource cleanup
2. **Use stealth mode** for sites with anti-bot protection
3. **Set appropriate rate limits** to avoid being blocked
4. **Use proxy rotation** for large-scale scraping
5. **Handle errors gracefully** in batch operations
6. **Choose the right concurrency** based on target site limits
7. **Persist cookies** when session state is needed
8. **Use async methods** for I/O-bound high-concurrency scraping

---

## Troubleshooting

### Connection Errors

```python
from http_client import ScraperClient, TransportError

try:
    with ScraperClient(timeout=10.0) as client:
        response = client.get("https://example.com")
except TransportError as e:
    print(f"Connection failed: {e}")
    if e.original_error:
        print(f"Original error: {e.original_error}")
```

### Rate Limit Errors (429)

```python
from http_client import ScraperClient

# Automatically retry on 429 with backoff
client = ScraperClient(
    retries=5,
    retry_codes=(429,),
    retry_backoff_base=3.0,  # Wait longer between retries
)
```

### SSL Certificate Errors

```python
from http_client import ScraperClient

# Disable SSL verification (not recommended for production)
client = ScraperClient(verify_ssl=False)
```

### Debugging Requests

```python
from http_client import ScraperClient

with ScraperClient() as client:
    response = client.get("https://httpbin.org/get")

    # Inspect request details
    print(f"Final URL: {response.url}")
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Elapsed: {response.elapsed}s")
    print(f"Cookies: {response.cookies}")
```
