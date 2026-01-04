# HTTP Client Usage Guide

A comprehensive guide to using the unified HTTPClient with per-request backend switching between httpx and curl_cffi.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Cookie Persistence](#cookie-persistence)
4. [Per-Request Backend Switching](#per-request-backend-switching)
5. [Stealth Mode](#stealth-mode)
6. [Async Operations](#async-operations)
7. [Helper Methods](#helper-methods)
8. [Header Management](#header-management)
9. [Proxy Configuration](#proxy-configuration)
10. [Error Handling](#error-handling)
11. [Real-World Examples](#real-world-examples)
12. [Configuration Reference](#configuration-reference)

---

## Quick Start

### Installation

```bash
# Install from GitHub
pip install git+https://github.com/iampramodphuyal/httphandler.git

# For stealth mode (curl backend)
pip install curl_cffi
```

### Minimal Example

```python
from http_client import HTTPClient

client = HTTPClient()
response = client.get("https://httpbin.org/get")
print(response.status_code)  # 200
print(response.text)
client.close()
```

---

## Basic Usage

### GET Request

```python
from http_client import HTTPClient

client = HTTPClient()

# Simple GET
response = client.get("https://httpbin.org/get")
print(response.text)

# GET with query parameters
response = client.get(
    "https://httpbin.org/get",
    params={"search": "python", "page": "1"}
)

# GET with custom headers
response = client.get(
    "https://httpbin.org/get",
    headers={"Authorization": "Bearer token123"}
)

client.close()
```

### POST Request

```python
from http_client import HTTPClient

client = HTTPClient()

# POST with JSON
response = client.post(
    "https://httpbin.org/post",
    json={"username": "john", "action": "login"}
)

# POST with form data
response = client.post(
    "https://httpbin.org/post",
    data={"field1": "value1", "field2": "value2"}
)

client.close()
```

### Other HTTP Methods

```python
from http_client import HTTPClient

client = HTTPClient()

# PUT
client.put("https://httpbin.org/put", json={"id": 1, "name": "Updated"})

# DELETE
client.delete("https://httpbin.org/delete")

# PATCH
client.patch("https://httpbin.org/patch", json={"field": "new_value"})

# HEAD
client.head("https://httpbin.org/get")

# OPTIONS
client.options("https://httpbin.org/get")

client.close()
```

### Context Manager

```python
from http_client import HTTPClient

# Automatic cleanup
with HTTPClient() as client:
    response = client.get("https://httpbin.org/get")
    print(response.json())
# Client automatically closed
```

---

## Cookie Persistence

### Enable Cookie Persistence

```python
from http_client import HTTPClient

# Enable cookie persistence
client = HTTPClient(persist_cookies=True)

# Request 1: Login (cookies stored)
client.post("https://example.com/login", json={"user": "john", "pass": "secret"})

# Request 2: Dashboard (cookies sent automatically)
response = client.get("https://example.com/dashboard")

# Request 3: Profile (same session)
response = client.get("https://example.com/profile")

client.close()
```

### Access Stored Cookies

```python
from http_client import HTTPClient

client = HTTPClient(persist_cookies=True)
client.get("https://httpbin.org/cookies/set?session=abc123")

# View all cookies by domain
print(client.cookies)
# {"httpbin.org": {"session": "abc123"}}

# Clear cookies for specific domain
client.clear_cookies("httpbin.org")

# Clear all cookies
client.clear_cookies()

client.close()
```

### Cookies Work Across Backends

```python
from http_client import HTTPClient

client = HTTPClient(persist_cookies=True)

# Login via httpx backend
client.post("https://example.com/login", json={"user": "john"})

# Access protected page via curl backend - cookies still sent!
response = client.get(
    "https://example.com/dashboard",
    backend="curl",
    stealth=True,
)

client.close()
```

---

## Per-Request Backend Switching

The key feature of HTTPClient is switching backends per-request while sharing session state.

### When to Use Each Backend

| Backend | Use Case |
|---------|----------|
| `httpx` (default) | APIs, general requests, speed-focused |
| `curl` | Protected sites, anti-bot bypass, stealth mode |

### Switching Backends

```python
from http_client import HTTPClient

client = HTTPClient(persist_cookies=True)

# Request 1: API call with httpx (fast)
resp1 = client.get("https://api.example.com/data")

# Request 2: Protected page with curl (stealth)
resp2 = client.get(
    "https://protected-site.com/page",
    backend="curl",
    stealth=True,
)

# Request 3: Back to httpx for API
resp3 = client.get("https://api.example.com/data")

# All three requests share the same cookie jar!
client.close()
```

### Set Default Backend

```python
from http_client import HTTPClient

# Default to curl backend
client = HTTPClient(default_backend="curl")

# Uses curl
response = client.get("https://example.com")

# Override to httpx for this request
response = client.get("https://api.example.com", backend="httpx")

client.close()
```

---

## Stealth Mode

Stealth mode applies browser fingerprinting when using the curl backend.

### Enable Stealth Mode

```python
from http_client import HTTPClient

client = HTTPClient(profile="chrome_120")

# Stealth request with browser fingerprinting
response = client.get(
    "https://protected-site.com",
    backend="curl",
    stealth=True,
)

client.close()
```

### Available Browser Profiles

```python
from http_client import HTTPClient

# Chrome profiles
client = HTTPClient(profile="chrome_120")  # or chrome_119, chrome_118

# Firefox profiles
client = HTTPClient(profile="firefox_121")  # or firefox_120, firefox_117

# Safari profiles
client = HTTPClient(profile="safari_17")  # or safari_16, safari_15

# Edge profiles
client = HTTPClient(profile="edge_120")  # or edge_119
```

### What Stealth Mode Does

When `stealth=True`:
- Applies browser-like headers (User-Agent, Accept, etc.)
- Orders headers like a real browser
- Includes Sec-CH-UA and Sec-Fetch headers (Chrome/Edge)
- Uses TLS fingerprint matching the browser profile

```python
from http_client import HTTPClient

client = HTTPClient(profile="chrome_120")

# Without stealth: minimal headers
resp1 = client.get("https://example.com", backend="curl")

# With stealth: full browser headers
resp2 = client.get("https://example.com", backend="curl", stealth=True)

client.close()
```

---

## Async Operations

### Simple Async Request

```python
import asyncio
from http_client import HTTPClient

async def main():
    async with HTTPClient() as client:
        response = await client.get_async("https://httpbin.org/get")
        print(response.json())

asyncio.run(main())
```

### Concurrent Async Requests

```python
import asyncio
from http_client import HTTPClient

async def fetch(client, url):
    response = await client.get_async(url)
    return response.json()

async def main():
    async with HTTPClient() as client:
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

### Async with Backend Switching

```python
import asyncio
from http_client import HTTPClient

async def main():
    async with HTTPClient(persist_cookies=True) as client:
        # Async request with httpx
        resp1 = await client.get_async("https://api.example.com")

        # Async request with curl stealth
        resp2 = await client.get_async(
            "https://protected-site.com",
            backend="curl",
            stealth=True,
        )

asyncio.run(main())
```

### All Async Methods

```python
await client.get_async(url, **kwargs)
await client.post_async(url, **kwargs)
await client.put_async(url, **kwargs)
await client.delete_async(url, **kwargs)
await client.patch_async(url, **kwargs)
await client.head_async(url, **kwargs)
await client.options_async(url, **kwargs)
await client.request_async(method, url, **kwargs)
```

---

## Helper Methods

Access information about the last response without storing it separately.

### Available Helpers

```python
from http_client import HTTPClient

client = HTTPClient()
response = client.get("https://httpbin.org/get")

# Status code from last response
print(client.get_status_code())  # 200

# Headers from last response
print(client.get_headers())  # {"Content-Type": "application/json", ...}

# Cookies from last response
print(client.get_cookies())  # {"session": "..."}

# Currently configured proxy
print(client.get_current_proxy())  # None or "http://proxy:8080"

# Request duration
print(client.get_elapsed())  # 0.234 (seconds)

# Full response object
resp = client.last_response
print(resp.text)

client.close()
```

### Chaining Requests

```python
from http_client import HTTPClient

client = HTTPClient()

client.post("https://example.com/login", json={"user": "john"})
if client.get_status_code() == 200:
    print("Login successful!")
    print(f"Session cookie: {client.get_cookies().get('session')}")

client.close()
```

---

## Header Management

### Default Headers

```python
from http_client import HTTPClient

# Set default headers at initialization
client = HTTPClient(headers={
    "User-Agent": "MyApp/1.0",
    "Accept": "application/json",
})

# All requests include these headers
client.get("https://example.com")
```

### Modify Default Headers

```python
from http_client import HTTPClient

client = HTTPClient()

# Add a default header
client.set_default_header("Authorization", "Bearer token123")

# Remove a default header
client.remove_default_header("Authorization")

client.close()
```

### Per-Request Headers

```python
from http_client import HTTPClient

client = HTTPClient(headers={"User-Agent": "MyApp/1.0"})

# Per-request headers merge with defaults
response = client.get(
    "https://example.com",
    headers={"X-Request-ID": "abc123"}
)
# Sends: User-Agent + X-Request-ID

client.close()
```

---

## Proxy Configuration

### Set Proxy at Initialization

```python
from http_client import HTTPClient

client = HTTPClient(proxy="http://proxy.example.com:8080")

# All requests use this proxy
client.get("https://example.com")

client.close()
```

### Per-Request Proxy

```python
from http_client import HTTPClient

client = HTTPClient()

# Use proxy for specific request
response = client.get(
    "https://example.com",
    proxy="socks5://localhost:1080"
)

client.close()
```

### Change Proxy at Runtime

```python
from http_client import HTTPClient

client = HTTPClient()

# Set proxy
client.set_proxy("http://proxy1:8080")
client.get("https://example.com")

# Change proxy
client.set_proxy("http://proxy2:8080")
client.get("https://example.com")

# Remove proxy
client.set_proxy(None)
client.get("https://example.com")  # Direct connection

client.close()
```

---

## Error Handling

### Exception Types

```python
from http_client import (
    HTTPClient,
    HTTPClientError,    # Base exception
    TransportError,     # Connection/timeout errors
    HTTPError,          # 4xx/5xx responses
    MaxRetriesExceeded, # Retries exhausted
)
```

### Handling Errors

```python
from http_client import HTTPClient, TransportError, HTTPError

client = HTTPClient()

try:
    response = client.get("https://example.com")
    response.raise_for_status()  # Raises HTTPError for 4xx/5xx
except TransportError as e:
    print(f"Connection failed: {e}")
except HTTPError as e:
    print(f"HTTP error: {e.response.status_code}")
finally:
    client.close()
```

### Checking Response Status

```python
from http_client import HTTPClient

client = HTTPClient()

response = client.get("https://httpbin.org/status/404")

# Check if successful (2xx)
if response.ok:
    print("Success!")
else:
    print(f"Failed: {response.status_code}")

# Or raise on error
try:
    response.raise_for_status()
except Exception as e:
    print(f"Error: {e}")

client.close()
```

---

## Real-World Examples

### Example 1: API Client

```python
from http_client import HTTPClient

class APIClient:
    def __init__(self, base_url, api_key):
        self.client = HTTPClient(headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        self.base_url = base_url

    def get_users(self):
        response = self.client.get(f"{self.base_url}/users")
        return response.json()

    def create_user(self, data):
        response = self.client.post(f"{self.base_url}/users", json=data)
        return self.client.get_status_code() == 201

    def close(self):
        self.client.close()

# Usage
api = APIClient("https://api.example.com", "my-api-key")
users = api.get_users()
api.create_user({"name": "John", "email": "john@example.com"})
api.close()
```

### Example 2: Web Scraper with Login

```python
from http_client import HTTPClient

with HTTPClient(persist_cookies=True) as client:
    # Step 1: Login with httpx
    response = client.post(
        "https://example.com/login",
        json={"username": "myuser", "password": "mypass"}
    )

    if response.ok:
        # Step 2: Access protected pages with curl stealth
        dashboard = client.get(
            "https://example.com/dashboard",
            backend="curl",
            stealth=True,
        )
        print(dashboard.text)
```

### Example 3: Mixed Backend Scraping

```python
from http_client import HTTPClient

with HTTPClient(persist_cookies=True, profile="chrome_120") as client:
    # Fast API calls with httpx
    api_data = client.get("https://api.example.com/products").json()

    for product in api_data["products"]:
        # Protected pages with curl stealth
        details = client.get(
            f"https://example.com/product/{product['id']}",
            backend="curl",
            stealth=True,
        )
        print(f"Product {product['id']}: {client.get_status_code()}")
```

### Example 4: Async Scraper

```python
import asyncio
from http_client import HTTPClient

async def scrape_urls(urls):
    async with HTTPClient() as client:
        tasks = [client.get_async(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        for url, resp in zip(urls, responses):
            if isinstance(resp, Exception):
                print(f"Failed: {url} - {resp}")
            elif resp.ok:
                successful.append(resp)

        return successful

async def main():
    urls = [f"https://httpbin.org/get?id={i}" for i in range(10)]
    results = await scrape_urls(urls)
    print(f"Successful: {len(results)}")

asyncio.run(main())
```

---

## Configuration Reference

### HTTPClient Options

```python
from http_client import HTTPClient

client = HTTPClient(
    # Backend selection
    default_backend="httpx",     # "httpx" or "curl"

    # Session
    persist_cookies=False,       # Enable cookie persistence

    # Timeouts
    timeout=30.0,                # Request timeout (seconds)

    # Headers
    headers=None,                # Default headers dict

    # SSL
    verify_ssl=True,             # Verify SSL certificates

    # Proxy
    proxy=None,                  # Default proxy URL

    # Redirects
    follow_redirects=True,       # Follow HTTP redirects

    # Stealth (curl backend)
    profile="chrome_120",        # Browser profile for fingerprinting
)
```

### Request Parameters

All request methods accept these parameters:

```python
client.get(
    url,                         # Required: URL to request
    headers=None,                # Per-request headers
    params=None,                 # URL query parameters
    cookies=None,                # Per-request cookies
    timeout=None,                # Request-specific timeout
    proxy=None,                  # Request-specific proxy
    backend=None,                # "httpx" or "curl"
    stealth=False,               # Apply fingerprinting (curl only)
)

# POST/PUT/PATCH also accept:
client.post(
    url,
    data=None,                   # Form data
    json=None,                   # JSON body
    **kwargs
)
```

### Response Object

```python
response.status_code    # HTTP status code (int)
response.headers        # Response headers (dict)
response.content        # Raw bytes
response.text           # Decoded text
response.url            # Final URL after redirects
response.cookies        # Response cookies (dict)
response.elapsed        # Request duration (float, seconds)
response.ok             # True if 2xx status
response.json()         # Parse as JSON
response.raise_for_status()  # Raise HTTPError if not ok
```

---

## Best Practices

1. **Use context managers** for automatic cleanup
2. **Enable `persist_cookies`** only when session state is needed
3. **Use httpx** (default) for APIs and speed-focused requests
4. **Use curl with stealth** for protected sites
5. **Set appropriate timeouts** for your use case
6. **Handle errors** gracefully with try/except
7. **Use async** for high-concurrency I/O-bound operations
8. **Share one client instance** across your application
