# HTTP Client

A unified Python HTTP client with per-request backend switching between httpx and curl_cffi. Features shared cookie persistence, optional browser fingerprinting, and both sync/async support.

## Features

- **Unified API**: Single `HTTPClient` class for all HTTP operations
- **Per-Request Backend Switching**: Use `httpx` (default) or `curl` per request
- **Shared Session State**: Cookies persist across both backends
- **Browser Fingerprinting**: Optional stealth mode with browserforge headers (both backends) and TLS fingerprinting (curl backend)
- **Verbose/Debug Mode**: Detailed request/response logging for debugging web scraping
- **Proxy Management**: Provider-based proxy system with rotation, health tracking, and auto-failover
- **Sync & Async**: Both synchronous and asynchronous methods
- **Helper Methods**: `get_status_code()`, `get_headers()`, `get_cookies()`, `get_current_proxy()`

## Installation

```bash
# Install latest version
pip install git+https://github.com/iampramodphuyal/httphandler.git

# For curl backend (optional, for stealth mode)
pip install curl_cffi
```

## Quick Start

### Basic Usage

```python
from http_client import HTTPClient

# Create client (httpx backend by default)
client = HTTPClient()

# Make requests
response = client.get("https://httpbin.org/get")
print(response.status_code)  # 200
print(response.text)

# Use helper methods
print(client.get_status_code())   # 200
print(client.get_headers())       # {"Content-Type": "application/json", ...}
print(client.get_cookies())       # {"session": "..."}

client.close()
```

### Cookie Persistence

```python
from http_client import HTTPClient

# Enable cookie persistence
client = HTTPClient(persist_cookies=True)

# Login (cookies stored automatically)
client.post("https://example.com/login", json={"user": "john", "pass": "secret"})

# Subsequent requests include cookies
client.get("https://example.com/dashboard")  # Cookies sent automatically

client.close()
```

### Per-Request Backend Switching

```python
from http_client import HTTPClient

client = HTTPClient(persist_cookies=True)

# Request 1: Use httpx (default, fast)
resp1 = client.get("https://api.example.com/data")

# Request 2: Use curl with stealth mode (for protected sites)
resp2 = client.get(
    "https://protected-site.com",
    backend="curl",
    stealth=True,
)

# Request 3: Back to httpx (cookies from resp2 available!)
resp3 = client.get("https://api.example.com/data")

client.close()
```

### Async Support

```python
import asyncio
from http_client import HTTPClient

async def main():
    async with HTTPClient() as client:
        response = await client.get_async("https://httpbin.org/get")
        print(response.json())

asyncio.run(main())
```

## API Reference

### HTTPClient Initialization

```python
HTTPClient(
    default_backend="httpx",     # "httpx" or "curl"
    persist_cookies=False,       # Enable cookie persistence
    timeout=30.0,                # Request timeout (seconds)
    headers=None,                # Default headers for all requests
    verify_ssl=True,             # SSL certificate verification
    proxy=None,                  # Default proxy URL
    follow_redirects=True,       # Follow HTTP redirects
    profile="chrome_120",        # Browser profile (stealth mode)
    http_version=None,           # "1.1", "2", or None (auto)
    verbose=False,               # Enable verbose debug output
    debug_callback=None,         # Callback for debug info (DebugInfo)
)
```

### Request Methods

All methods support these parameters:
- `headers`: Per-request headers (merged with defaults)
- `params`: URL query parameters
- `cookies`: Per-request cookies (merged with stored cookies)
- `timeout`: Request-specific timeout
- `proxy`: Request-specific proxy
- `backend`: `"httpx"` or `"curl"` (overrides default)
- `stealth`: Apply browser fingerprinting (browserforge headers on both backends, TLS fingerprinting on curl only)

```python
# Sync methods
client.get(url, **kwargs)
client.post(url, data=None, json=None, **kwargs)
client.put(url, data=None, json=None, **kwargs)
client.delete(url, **kwargs)
client.patch(url, data=None, json=None, **kwargs)
client.head(url, **kwargs)
client.options(url, **kwargs)

# Async methods (add _async suffix)
await client.get_async(url, **kwargs)
await client.post_async(url, **kwargs)
# ... etc
```

### Helper Methods

```python
client.get_status_code()      # Last response status code
client.get_headers()          # Last response headers
client.get_cookies()          # Last response cookies
client.get_current_proxy()    # Currently configured proxy
client.get_elapsed()          # Last request duration (seconds)
client.last_response          # Full Response object
```

### Cookie Management

```python
client.cookies                # All stored cookies by domain
client.clear_cookies()        # Clear all cookies
client.clear_cookies("domain.com")  # Clear domain-specific
```

### Header Management

```python
client.set_default_header("X-Custom", "value")
client.remove_default_header("X-Custom")
```

### Verbose/Debug Mode

Enable verbose mode to see detailed request/response information - useful for debugging web scraping and anti-bot bypass:

```python
from http_client import HTTPClient, DebugInfo

# Enable at initialization
client = HTTPClient(verbose=True)

# Or enable/disable at runtime
client.verbose = True   # Enable
client.verbose = False  # Disable

# Check status
if client.verbose:
    print("Verbose mode is on")

# Make request - debug output printed to stderr
response = client.get("https://example.com", backend="curl", stealth=True)
```

**Verbose output includes:**
- Request method, URL, backend used
- Stealth mode status and browser profile
- HTTP version
- All request headers (including browserforge-generated)
- Cookies sent
- Proxy used
- Response status and timing
- Response headers
- Cookies received
- TLS impersonate info (curl backend)
- Body preview (first 500 chars)

**Programmatic capture with callback:**

```python
from http_client import HTTPClient, DebugInfo

def my_callback(info: DebugInfo):
    print(f"{info.method} {info.url} -> {info.status_code} ({info.elapsed:.2f}s)")
    print(f"Headers sent: {list(info.request_headers.keys())}")

client = HTTPClient(verbose=True, debug_callback=my_callback)
client.get("https://httpbin.org/get")
client.close()
```

### Proxy Management

```python
# Simple proxy URL
client.set_proxy("http://proxy:8080")

# Multiple proxies with rotation
client.set_proxy(proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"])

# Rotate to next proxy
client.switch_proxy()

# Check current proxy
print(client.get_current_proxy())  # "http://p2:8080"

# Remove proxy
client.reset_proxy()
```

### Advanced Proxy Management

```python
from http_client import HTTPClient, GenericProvider

# Create provider with metadata
provider = GenericProvider(proxies=[
    {"url": "http://us1:8080", "country": "US", "proxy_type": "datacenter"},
    {"url": "http://us2:8080", "country": "US", "proxy_type": "datacenter"},
    {"url": "http://gb1:8080", "country": "GB", "proxy_type": "residential"},
])

client = HTTPClient()
client.add_proxy_provider(provider)

# Set proxy with filters
client.set_proxy(provider="generic", country="US", proxy_type="datacenter")

# Access proxy manager for stats
stats = client.proxy_manager.get_stats()
print(f"Healthy: {stats.healthy_proxies}/{stats.total_proxies}")
print(f"Success rate: {stats.success_rate:.1%}")
```

**Features:**
- **Round-robin rotation**: `switch_proxy()` cycles through healthy proxies
- **Health tracking**: Proxies marked unhealthy after 3 consecutive failures
- **Auto-failover**: Unhealthy proxies get 60s cooldown, then auto-recover
- **Provider abstraction**: Easy to extend with custom providers (BrightData, Oxylabs, etc.)

### Async Proxy Methods

```python
async with HTTPClient() as client:
    await client.set_proxy_async(proxies=["http://p1:8080", "http://p2:8080"])
    proxy = await client.get_current_proxy_async()
    await client.switch_proxy_async()
    await client.reset_proxy_async()
```

## Backends

### httpx (Default)

- Fast and reliable
- HTTP/2 support
- Browserforge headers with `stealth=True`
- Best for APIs and general use

### curl (Full Stealth Mode)

- TLS fingerprinting via curl_cffi
- Browserforge headers with `stealth=True`
- Custom headers override generated headers
- Best for protected sites with anti-bot measures (Cloudflare, Akamai, etc.)

### Stealth Mode Comparison

| Feature | httpx + stealth | curl + stealth |
|---------|-----------------|----------------|
| Browserforge headers | ✅ | ✅ |
| TLS fingerprinting | ❌ | ✅ |
| HTTP/2 | ✅ | ✅ |
| Best for | Header-only checks | Full anti-bot bypass |

```python
# httpx with stealth (browserforge headers, no TLS fingerprinting)
response = client.get(
    "https://example.com",
    stealth=True,
)

# curl with full stealth (browserforge headers + TLS fingerprinting)
response = client.get(
    "https://protected-site.com",
    backend="curl",
    stealth=True,
)

# Custom headers override browserforge-generated headers (case-insensitive)
response = client.get(
    "https://protected-site.com",
    stealth=True,
    headers={"user-agent": "MyCustomAgent/1.0"},  # Overrides generated User-Agent
)
```

**Browserforge features:**
- Desktop platforms only: Windows, macOS, Linux (equal distribution)
- Custom headers override generated headers (case-insensitive matching)
- Realistic Sec-Fetch-*, Accept-*, and security headers

Available browser profiles for stealth mode:
- Chrome: `chrome_120`, `chrome_119`, `chrome_118`
- Firefox: `firefox_121`, `firefox_120`, `firefox_117`
- Safari: `safari_17`, `safari_16`, `safari_15`
- Edge: `edge_120`, `edge_119`

## Error Handling

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

## Context Managers

```python
# Sync
with HTTPClient() as client:
    response = client.get("https://example.com")
# Auto-cleanup

# Async
async with HTTPClient() as client:
    response = await client.get_async("https://example.com")
# Auto-cleanup
```

## Package Structure

```
http_client/
├── __init__.py          # Public API: HTTPClient, Response, DebugInfo, exceptions
├── client.py            # Unified HTTPClient class
├── models.py            # Request, Response, exceptions
├── _debug.py            # DebugInfo and verbose output handling
├── _backends/           # Internal backend implementations
│   ├── httpx_backend.py # httpx wrapper
│   └── curl_backend.py  # curl_cffi wrapper with stealth
├── _cookies.py          # Thread-safe cookie storage
├── _fingerprint/        # Browser profiles for stealth mode
└── _proxy/              # Proxy management with provider abstraction
    ├── manager.py       # ProxyManager (pool, rotation, health)
    ├── base.py          # Abstract ProxyProvider class
    └── providers/       # Provider implementations
```

## Development

```bash
# Clone repository
git clone https://github.com/iampramodphuyal/httphandler.git
cd httphandler

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy http_client
```

## Documentation

See [USAGE.md](USAGE.md) for comprehensive documentation including:
- Complete API reference
- Per-request backend switching examples
- Cookie persistence patterns
- Stealth mode configuration
- Error handling best practices

## License

MIT License
