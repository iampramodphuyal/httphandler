# HTTP Client Usage Guide

A comprehensive guide to using the HTTP client package, from simple requests to advanced web scraping with thread pools, async operations, and browser fingerprinting.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [HTTPHandler - Simple Interface (Beginner)](#httphandler---simple-interface-beginner)
   - [Basic Requests](#basic-requests)
   - [Response Helpers](#response-helpers)
   - [Session Management](#session-management)
   - [Header Management](#header-management)
   - [Proxy Control](#proxy-control)
   - [Streaming Downloads](#streaming-downloads)
   - [Context Managers](#context-managers)
3. [ScraperClient - Advanced Interface](#scraperclient---advanced-interface)
   - [Speed vs Stealth Modes](#speed-vs-stealth-modes)
   - [Browser Fingerprinting](#browser-fingerprinting)
   - [Cookie Persistence](#cookie-persistence)
4. [Async Operations](#async-operations)
   - [Simple Async Requests](#simple-async-requests)
   - [Concurrent Async Requests](#concurrent-async-requests)
   - [Async Batch Operations](#async-batch-operations)
5. [Thread Pool Operations](#thread-pool-operations)
   - [Batch Requests with Thread Pool](#batch-requests-with-thread-pool)
   - [Custom Request Objects](#custom-request-objects)
6. [Thread Safety](#thread-safety)
   - [Rate Limiter Thread Safety](#rate-limiter-thread-safety)
   - [Proxy Pool Thread Safety](#proxy-pool-thread-safety)
   - [Cookie Store Thread Safety](#cookie-store-thread-safety)
7. [Proxy Rotation](#proxy-rotation)
8. [Rate Limiting](#rate-limiting)
9. [Error Handling](#error-handling)
10. [Real-World Examples](#real-world-examples)
11. [Configuration Reference](#configuration-reference)

---

## Quick Start

### Installation

```bash
# Install from GitHub
pip install git+https://github.com/iampramodphuyal/httphandler.git

# Or with specific version
pip install git+https://github.com/iampramodphuyal/httphandler.git@v0.3.0
```

### Choose Your Interface

| Interface | Use Case | Complexity |
|-----------|----------|------------|
| `HTTPHandler` | Simple HTTP requests, API calls, basic scraping | Beginner |
| `ScraperClient` | Advanced scraping, anti-bot bypass, fingerprinting | Advanced |

```python
# Simple (Beginner)
from http_client import HTTPHandler

handler = HTTPHandler()
handler.get("https://example.com", headers={"User-Agent": "MyApp/1.0"})
print(handler.get_status_code())

# Advanced
from http_client import ScraperClient

client = ScraperClient(mode="stealth", profile="chrome_120")
response = client.get("https://example.com")
```

---

## HTTPHandler - Simple Interface (Beginner)

`HTTPHandler` provides a clean, intuitive interface for HTTP requests with built-in session management and helper methods.

### Basic Requests

#### GET Request

```python
from http_client import HTTPHandler

handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})

# Simple GET
response = handler.get("https://httpbin.org/get")
print(response.text)
print(response.status_code)

# GET with query parameters
response = handler.get(
    "https://httpbin.org/get",
    params={"search": "python", "page": "1"}
)

handler.close()
```

#### POST Request

```python
from http_client import HTTPHandler

handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})

# POST with JSON
response = handler.post(
    "https://httpbin.org/post",
    json={"username": "john", "action": "login"}
)

# POST with form data
response = handler.post(
    "https://httpbin.org/post",
    data={"field1": "value1", "field2": "value2"}
)

handler.close()
```

#### Other HTTP Methods

```python
from http_client import HTTPHandler

handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})

# PUT
handler.put("https://httpbin.org/put", json={"id": 1, "name": "Updated"})

# DELETE
handler.delete("https://httpbin.org/delete")

# PATCH
handler.patch("https://httpbin.org/patch", json={"field": "new_value"})

# HEAD
handler.head("https://httpbin.org/get")

# OPTIONS
handler.options("https://httpbin.org/get")

handler.close()
```

### Response Helpers

After making a request, use helper methods to access response data:

```python
from http_client import HTTPHandler

handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})
response = handler.get("https://httpbin.org/get")

# Status code
print(handler.get_status_code())  # 200

# Response headers
print(handler.get_headers())  # {"Content-Type": "application/json", ...}

# Cookies from response
print(handler.get_cookies())  # {"session": "abc123", ...}

# Request timing
print(handler.get_elapsed())  # 0.234 (seconds)

# Response size
print(handler.get_content_length())  # 1024 (bytes)

# Bandwidth (bytes/second)
print(handler.get_bandwidth())  # 4376.07

# Full response object
resp = handler.get_response()
print(resp.text)
print(resp.json())

handler.close()
```

### Session Management

Control cookie persistence across requests:

```python
from http_client import HTTPHandler

# Default: stateless (no cookie persistence)
handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})

# Enable session persistence
handler.persist_session = True

# Request 1: Login (cookies will be stored)
handler.post("https://example.com/login", data={"user": "john", "pass": "secret"})

# Request 2: Dashboard (cookies automatically included)
handler.get("https://example.com/dashboard")

# Request 3: Profile (same session)
handler.get("https://example.com/profile")

# Reset session (clear cookies) for independent requests
handler.reset_session()

# Request 4-5: Fresh session
handler.get("https://example.com/public/page1")
handler.get("https://example.com/public/page2")

handler.close()
```

#### Mixed Session Workflow

```python
from http_client import HTTPHandler

handler = HTTPHandler(persist_session=True, headers={"User-Agent": "MyApp/1.0"})

# Requests 1-3: Same session
handler.get("https://example.com/step1")
handler.get("https://example.com/step2")
handler.get("https://example.com/step3")

# Reset for independent requests
handler.reset_session()

# Requests 4-5: Fresh session
handler.get("https://example.com/independent1")
handler.get("https://example.com/independent2")

handler.close()
```

#### Clear Cookies for Specific Domain

```python
from http_client import HTTPHandler

handler = HTTPHandler(persist_session=True, headers={"User-Agent": "MyApp/1.0"})

# Make requests to multiple domains
handler.get("https://site1.com/page")
handler.get("https://site2.com/page")

# Clear cookies for site1 only
handler.clear_cookies("site1.com")

# site2 cookies still present
handler.get("https://site2.com/page")  # Cookies included

handler.close()
```

### Header Management

Set, modify, and clear default headers:

```python
from http_client import HTTPHandler

# Initialize with default headers
handler = HTTPHandler(headers={
    "User-Agent": "MyApp/1.0",
    "Accept": "application/json"
})

# Add a header
handler.add_header("Authorization", "Bearer token123")

# Get current default headers
print(handler.get_default_headers())
# {"User-Agent": "MyApp/1.0", "Accept": "application/json", "Authorization": "Bearer token123"}

# Replace all default headers
handler.set_headers({
    "User-Agent": "NewApp/2.0",
    "X-Custom": "value"
})

# Remove a specific header
handler.remove_header("X-Custom")

# Clear all default headers
handler.clear_headers()

# Request-specific headers (merged with defaults)
handler.set_headers({"User-Agent": "MyApp/1.0"})
handler.get("https://example.com", headers={"X-Request-ID": "abc123"})
# Sends: User-Agent + X-Request-ID

handler.close()
```

#### Warning for Missing Headers

If you make a request without any headers, a warning is issued:

```python
from http_client import HTTPHandler

handler = HTTPHandler()  # No default headers

# This will print a warning:
# "Warning: No headers provided. Request may be detected as bot traffic."
handler.get("https://example.com")

handler.close()
```

### Proxy Control

Configure and toggle proxy usage:

```python
from http_client import HTTPHandler

# Initialize with proxy
handler = HTTPHandler(
    proxy="socks5://localhost:1080",
    headers={"User-Agent": "MyApp/1.0"}
)

# Check proxy status
print(handler.proxy_enabled)  # True
print(handler.proxy)  # "socks5://localhost:1080"

# Temporarily disable proxy
handler.disable_proxy()
handler.get("https://example.com")  # Direct connection

# Re-enable proxy
handler.enable_proxy()
handler.get("https://example.com")  # Through proxy

# Change proxy
handler.set_proxy("http://newproxy:8080")

# Remove proxy
handler.set_proxy(None)

handler.close()
```

### Streaming Downloads

Download large files without loading into memory:

```python
from http_client import HTTPHandler

handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})

# Stream to file
with open("large_file.zip", "wb") as f:
    for chunk in handler.stream("https://example.com/large_file.zip", chunk_size=8192):
        f.write(chunk)

# Stream with progress callback
def progress(chunk, downloaded, total):
    percent = (downloaded / total) * 100 if total else 0
    print(f"Downloaded: {downloaded}/{total} bytes ({percent:.1f}%)")

for chunk in handler.stream(
    "https://example.com/file.zip",
    chunk_size=8192,
    callback=progress
):
    pass  # Process chunk

handler.close()
```

### Context Managers

Automatic resource cleanup with context managers:

```python
from http_client import HTTPHandler

# Basic context manager
with HTTPHandler(headers={"User-Agent": "MyApp/1.0"}) as handler:
    handler.get("https://example.com")
    print(handler.get_status_code())
# Handler automatically closed

# Scoped session (auto-resets on exit)
handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})

with handler.session() as session:
    session.get("https://example.com/step1")
    session.get("https://example.com/step2")
    # Cookies accumulated within this scope

# Session automatically reset here
# Original handler state restored

handler.close()
```

---

## ScraperClient - Advanced Interface

`ScraperClient` provides advanced features for web scraping including browser fingerprinting, rate limiting, proxy rotation, and stealth capabilities.

### Speed vs Stealth Modes

#### Speed Mode (Default)

Optimized for maximum throughput:

```python
from http_client import ScraperClient

client = ScraperClient(
    mode="speed",
    rate_limit=0,        # No rate limiting
    retries=1,           # Minimal retries
    max_workers=50,      # High thread pool
)

with client:
    results = client.gather_sync(urls)
```

**Speed mode characteristics:**
- No artificial delays
- Minimal headers
- No TLS fingerprinting
- Best for APIs and non-protected sites

#### Stealth Mode

Mimics real browser behavior:

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
    response = client.get("https://example.com")
```

**Stealth mode characteristics:**
- Random delays between requests
- Full browser-like headers
- TLS fingerprint matches real browsers
- Automatic referer chain
- Best for protected sites

### Browser Fingerprinting

```python
from http_client import ScraperClient, PROFILES, get_profile

# Available profiles
print("Available profiles:")
for name in sorted(PROFILES.keys()):
    print(f"  - {name}")
# chrome_120, chrome_119, firefox_121, safari_17, edge_120, etc.

# Use specific profile
client = ScraperClient(mode="stealth", profile="firefox_121")

# Get profile details
profile = get_profile("chrome_120")
print(f"User-Agent: {profile.user_agent}")
print(f"Sec-CH-UA: {profile.sec_ch_ua}")
```

### Cookie Persistence

```python
from http_client import ScraperClient

# Enable cookie persistence
with ScraperClient(persist_cookies=True) as client:
    # Login
    client.post("https://example.com/login", data={"user": "john"})

    # Subsequent requests include cookies
    response = client.get("https://example.com/dashboard")

    # Access cookie store
    if client.cookie_store:
        all_cookies = client.cookie_store.get_all()
        print(all_cookies)
```

---

## Async Operations

### Simple Async Requests

```python
import asyncio
from http_client import ScraperClient

async def main():
    async with ScraperClient() as client:
        response = await client.get_async("https://httpbin.org/get")
        print(response.json())

asyncio.run(main())
```

### Concurrent Async Requests

```python
import asyncio
from http_client import ScraperClient

async def fetch(client, url):
    response = await client.get_async(url)
    return response.json()

async def main():
    async with ScraperClient() as client:
        # Run multiple requests concurrently
        results = await asyncio.gather(
            fetch(client, "https://httpbin.org/get?id=1"),
            fetch(client, "https://httpbin.org/get?id=2"),
            fetch(client, "https://httpbin.org/get?id=3"),
        )
        for result in results:
            print(result)

asyncio.run(main())
```

### Async Batch Operations

Use `gather_async()` for high-concurrency scraping with semaphore control:

```python
import asyncio
from http_client import ScraperClient

async def main():
    urls = [f"https://httpbin.org/get?page={i}" for i in range(100)]

    async with ScraperClient() as client:
        # Limit to 20 concurrent requests
        results = await client.gather_async(urls, concurrency=20)

        print(f"Successful: {results.success_count}")
        print(f"Failed: {results.failure_count}")

        for i, response in enumerate(results.responses):
            if response:
                print(f"URL {i}: {response.status_code}")

asyncio.run(main())
```

#### Async with Stop on Error

```python
import asyncio
from http_client import ScraperClient

async def main():
    urls = ["https://httpbin.org/get", "https://invalid.url", "https://httpbin.org/get"]

    async with ScraperClient() as client:
        results = await client.gather_async(urls, stop_on_error=True)
        # Processing stops after first error

asyncio.run(main())
```

---

## Thread Pool Operations

### Batch Requests with Thread Pool

Use `gather_sync()` for concurrent requests using a thread pool:

```python
from http_client import ScraperClient

urls = [
    "https://httpbin.org/get?page=1",
    "https://httpbin.org/get?page=2",
    "https://httpbin.org/get?page=3",
    "https://httpbin.org/get?page=4",
    "https://httpbin.org/get?page=5",
]

# Configure thread pool size
with ScraperClient(max_workers=10) as client:
    results = client.gather_sync(urls)

    print(f"Successful: {results.success_count}")
    print(f"Failed: {results.failure_count}")

    for i, response in enumerate(results.responses):
        if response:
            print(f"URL {i}: Status {response.status_code}")

    # Check errors
    for idx, error in results.errors.items():
        print(f"URL {idx} failed: {error}")
```

### Custom Request Objects

```python
from http_client import ScraperClient, Request

requests = [
    Request(method="GET", url="https://httpbin.org/get"),
    Request(method="POST", url="https://httpbin.org/post", json={"id": 1}),
    Request(method="POST", url="https://httpbin.org/post", json={"id": 2}),
    Request(
        method="GET",
        url="https://httpbin.org/headers",
        headers={"X-Custom": "value"}
    ),
]

with ScraperClient(max_workers=5) as client:
    results = client.gather_sync(requests)

    for response in results.responses:
        if response:
            print(response.json())
```

---

## Thread Safety

The package is designed to be thread-safe for concurrent access from multiple threads.

### Rate Limiter Thread Safety

The rate limiter uses a dual-lock pattern for both thread and async safety:

```python
from http_client import ScraperClient
from concurrent.futures import ThreadPoolExecutor

def make_request(client, url):
    # Rate limiter is thread-safe
    response = client.get(url)
    return response.status_code

# Rate limiter shared across threads
client = ScraperClient(rate_limit=2.0)  # 2 req/sec per domain

with client:
    with ThreadPoolExecutor(max_workers=10) as executor:
        urls = [f"https://httpbin.org/get?id={i}" for i in range(20)]
        futures = [executor.submit(make_request, client, url) for url in urls]

        for future in futures:
            print(future.result())
```

### Proxy Pool Thread Safety

Proxy pool operations are protected by threading locks:

```python
from http_client import ScraperClient
from concurrent.futures import ThreadPoolExecutor

client = ScraperClient(
    proxies=[
        "http://proxy1:8080",
        "http://proxy2:8080",
        "http://proxy3:8080",
    ],
    proxy_strategy="round_robin",
)

def fetch_with_proxy(url):
    # Proxy selection is thread-safe
    response = client.get(url)
    return response.status_code

with client:
    with ThreadPoolExecutor(max_workers=10) as executor:
        urls = [f"https://httpbin.org/ip?id={i}" for i in range(30)]
        results = list(executor.map(fetch_with_proxy, urls))
        print(results)
```

### Cookie Store Thread Safety

Cookie store is safe for concurrent access:

```python
from http_client import ScraperClient
from concurrent.futures import ThreadPoolExecutor, as_completed

client = ScraperClient(persist_cookies=True)

def fetch_page(url):
    # Cookie operations are thread-safe
    return client.get(url).status_code

with client:
    with ThreadPoolExecutor(max_workers=5) as executor:
        urls = [f"https://httpbin.org/cookies/set?key{i}=value{i}" for i in range(10)]
        futures = {executor.submit(fetch_page, url): url for url in urls}

        for future in as_completed(futures):
            url = futures[future]
            try:
                status = future.result()
                print(f"{url}: {status}")
            except Exception as e:
                print(f"{url}: Error - {e}")

    # All cookies collected safely
    if client.cookie_store:
        print(f"Total cookies: {len(client.cookie_store)}")
```

### Using Both Async and Threads

The package supports mixed async and threaded operations:

```python
import asyncio
from http_client import ScraperClient

async def async_batch():
    async with ScraperClient() as client:
        urls = [f"https://httpbin.org/get?async={i}" for i in range(10)]
        results = await client.gather_async(urls, concurrency=5)
        return results.success_count

def sync_batch():
    with ScraperClient(max_workers=5) as client:
        urls = [f"https://httpbin.org/get?sync={i}" for i in range(10)]
        results = client.gather_sync(urls)
        return results.success_count

# Can run both patterns
async_count = asyncio.run(async_batch())
sync_count = sync_batch()

print(f"Async: {async_count}, Sync: {sync_count}")
```

---

## Proxy Rotation

### Basic Proxy Pool

```python
from http_client import ScraperClient

client = ScraperClient(
    proxies=[
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        "socks5://proxy3.example.com:1080",
    ],
    proxy_strategy="round_robin",  # or "random", "least_used"
)

with client:
    for i in range(6):
        response = client.get("https://httpbin.org/ip")
        print(f"Request {i}: {response.json()['origin']}")
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

    # Check proxy status
    if client.proxy_pool:
        stats = client.proxy_pool.get_stats()
        print(f"Available: {stats['available']}/{stats['total']}")

        for proxy in stats['proxies']:
            print(f"  {proxy['url']}: enabled={proxy['enabled']}")
```

---

## Rate Limiting

### Per-Domain Rate Limiting

```python
from http_client import ScraperClient

# 2 requests per second per domain
client = ScraperClient(rate_limit=2.0)

with client:
    # Rate-limited to 2/sec for example.com
    for i in range(10):
        client.get(f"https://example.com/page/{i}")
```

### Custom Domain Rates

```python
from http_client import ScraperClient

client = ScraperClient(rate_limit=1.0)  # Default: 1 req/sec

with client:
    if client.rate_limiter:
        # Higher rate for API
        client.rate_limiter.set_domain_rate("api.example.com", 10.0)
        # Lower rate for protected site
        client.rate_limiter.set_domain_rate("slow.example.com", 0.5)
```

---

## Error Handling

### Exception Types

```python
from http_client import (
    ScraperClient,
    HTTPHandler,
    TransportError,       # Connection/timeout errors
    HTTPError,            # 4xx/5xx responses
    MaxRetriesExceeded,   # All retries failed
    RateLimitExceeded,    # Rate limit hit
    AllProxiesFailed,     # No working proxies
    NoResponseError,      # HTTPHandler: no request made yet
)
```

### Handling Errors

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
    except TransportError as e:
        print(f"Connection failed: {e}")
    except HTTPError as e:
        print(f"HTTP error {e.response.status_code}")
    except MaxRetriesExceeded as e:
        print(f"Retries exhausted for {e.url}")
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

    # Process successes
    for i, response in enumerate(results.responses):
        if response:
            print(f"URL {i}: Success")

    # Handle errors
    for idx, error in results.errors.items():
        print(f"URL {idx}: {error}")

    # Raise first error if needed
    if not results.all_succeeded:
        results.raise_on_error()
```

---

## Real-World Examples

### Example 1: API Client with Session

```python
from http_client import HTTPHandler

class APIClient:
    def __init__(self, base_url, api_key):
        self.handler = HTTPHandler(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "MyAPIClient/1.0"
            }
        )
        self.base_url = base_url

    def get_users(self):
        self.handler.get(f"{self.base_url}/users")
        return self.handler.get_response().json()

    def create_user(self, data):
        self.handler.post(f"{self.base_url}/users", json=data)
        return self.handler.get_status_code() == 201

    def close(self):
        self.handler.close()

# Usage
client = APIClient("https://api.example.com", "my-api-key")
users = client.get_users()
client.create_user({"name": "John", "email": "john@example.com"})
client.close()
```

### Example 2: Web Scraper with Login

```python
from http_client import ScraperClient

with ScraperClient(persist_cookies=True, mode="stealth") as client:
    # Step 1: Get login page
    client.get("https://example.com/login")

    # Step 2: Submit login
    response = client.post(
        "https://example.com/login",
        data={"username": "myuser", "password": "mypass"}
    )

    if response.ok:
        # Step 3: Access protected pages
        dashboard = client.get("https://example.com/dashboard")
        profile = client.get("https://example.com/profile")

        print(dashboard.text)
        print(profile.text)
```

### Example 3: High-Performance Async Scraper

```python
import asyncio
from http_client import ScraperClient

async def scrape_urls(urls, concurrency=50):
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

### Example 4: Scraping with Proxy Rotation

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
            print(f"Product {i}: {response.status_code}")
```

### Example 5: Download with Progress

```python
from http_client import HTTPHandler

handler = HTTPHandler(headers={"User-Agent": "Downloader/1.0"})

def download_file(url, filename):
    downloaded = 0

    def progress(chunk, total, length):
        nonlocal downloaded
        downloaded = total
        if length:
            percent = (total / length) * 100
            print(f"\rDownloading: {percent:.1f}%", end="", flush=True)

    with open(filename, "wb") as f:
        for chunk in handler.stream(url, chunk_size=8192, callback=progress):
            f.write(chunk)

    print(f"\nDownloaded {downloaded} bytes to {filename}")

download_file("https://example.com/large_file.zip", "downloaded.zip")
handler.close()
```

---

## Configuration Reference

### HTTPHandler Options

```python
from http_client import HTTPHandler

handler = HTTPHandler(
    persist_session=False,     # Cookie persistence (default: False)
    timeout=30.0,              # Request timeout in seconds
    connect_timeout=10.0,      # Connection timeout
    verify_ssl=True,           # SSL certificate verification
    http_version="auto",       # "1.1", "2", or "auto"
    proxy=None,                # Proxy URL
    max_retries=3,             # Retry attempts
    headers=None,              # Default headers dict
    retry_codes=(429, 500, 502, 503, 504),  # Status codes to retry
    retry_backoff_base=2.0,    # Exponential backoff base
)
```

### ScraperClient Options

```python
from http_client import ScraperClient

client = ScraperClient(
    # Mode
    mode="speed",                # "speed" or "stealth"

    # Session
    persist_cookies=False,       # Cookie persistence

    # Fingerprinting
    profile="chrome_120",        # Browser profile

    # Rate Limiting
    rate_limit=2.0,              # Requests/second per domain (0=disabled)

    # Timeouts
    timeout=30.0,                # Total request timeout
    connect_timeout=10.0,        # Connection timeout

    # Retries
    retries=3,                   # Retry attempts
    retry_codes=(429, 500, 502, 503, 504, 520, 521, 522, 523, 524),
    retry_backoff_base=2.0,      # Exponential backoff

    # Proxies
    proxies=None,                # List of proxy URLs
    proxy_strategy="round_robin", # "round_robin", "random", "least_used"
    proxy_max_failures=3,        # Failures before disabling
    proxy_cooldown=300.0,        # Seconds before re-enabling

    # Concurrency
    max_workers=10,              # Thread pool size (gather_sync)
    default_concurrency=10,      # Semaphore limit (gather_async)

    # Stealth Mode Delays
    min_delay=1.0,               # Minimum random delay
    max_delay=3.0,               # Maximum random delay

    # SSL/Redirects
    verify_ssl=True,             # Verify SSL certificates
    follow_redirects=True,       # Follow HTTP redirects
    max_redirects=10,            # Maximum redirects

    # HTTP Version
    http_version="auto",         # "1.1", "2", or "auto"

    # Default Headers
    default_headers={},          # Headers for all requests
)
```

---

## Best Practices

1. **Always close handlers/clients** - Use context managers (`with`) for automatic cleanup
2. **Set User-Agent headers** - Avoid bot detection warnings
3. **Use stealth mode** for protected sites with anti-bot measures
4. **Set appropriate rate limits** to avoid being blocked
5. **Use proxy rotation** for large-scale scraping
6. **Handle errors gracefully** in batch operations
7. **Choose the right concurrency** based on target site limits
8. **Use async for I/O-bound** high-concurrency scraping
9. **Use thread pools for CPU-bound** or blocking operations
10. **Enable cookie persistence** only when session state is needed

---

## Troubleshooting

### Connection Timeouts

```python
# Increase timeouts
handler = HTTPHandler(timeout=60.0, connect_timeout=30.0)
```

### SSL Certificate Errors

```python
# Disable SSL verification (not recommended for production)
handler = HTTPHandler(verify_ssl=False)
```

### Rate Limit Errors (429)

```python
# Retry with longer backoff
client = ScraperClient(
    retries=5,
    retry_codes=(429,),
    retry_backoff_base=3.0,
)
```

### Bot Detection

```python
# Use stealth mode with realistic fingerprint
client = ScraperClient(
    mode="stealth",
    profile="chrome_120",
    min_delay=2.0,
    max_delay=5.0,
)
```
