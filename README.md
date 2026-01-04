# HTTP Client

A unified Python HTTP client with per-request backend switching between httpx and curl_cffi. Features shared cookie persistence, optional browser fingerprinting, and both sync/async support.

## Features

- **Unified API**: Single `HTTPClient` class for all HTTP operations
- **Per-Request Backend Switching**: Use `httpx` (default) or `curl` per request
- **Shared Session State**: Cookies persist across both backends
- **Browser Fingerprinting**: Optional stealth mode with browserforge headers (both backends) and TLS fingerprinting (curl backend)
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
    profile="chrome_120",        # Browser profile (curl stealth mode)
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

### Header & Proxy Management

```python
client.set_default_header("X-Custom", "value")
client.remove_default_header("X-Custom")
client.set_proxy("http://proxy:8080")
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

# Custom headers override browserforge-generated headers
response = client.get(
    "https://protected-site.com",
    stealth=True,
    headers={"User-Agent": "MyCustomAgent/1.0"},  # Overrides generated User-Agent
)
```

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
├── __init__.py          # Public API: HTTPClient, Response, exceptions
├── client.py            # Unified HTTPClient class
├── models.py            # Request, Response, exceptions
├── _backends/           # Internal backend implementations
│   ├── httpx_backend.py # httpx wrapper
│   └── curl_backend.py  # curl_cffi wrapper with stealth
├── _cookies.py          # Thread-safe cookie storage
└── _fingerprint/        # Browser profiles for stealth mode
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
