# HTTP Client

A Python HTTP client package designed for web scraping, supporting both asyncio and thread pool execution models with TLS fingerprinting, stealth capabilities, and robust safety guarantees.

## Features

- **Dual Execution Model**: Supports both asyncio (async/await) and ThreadPoolExecutor
- **TLS Fingerprint Impersonation**: Uses curl_cffi to mimic real browsers (Chrome, Firefox, Safari, Edge)
- **Two Operating Modes**:
  - **Speed Mode**: No artificial delays, minimal headers, max concurrency
  - **Stealth Mode**: Random delays, full browser headers, proxy rotation, referer chain building
- **Thread-safe & Async-safe**: All shared state (rate limiters, proxy pools, cookies) is protected
- **Rate Limiting**: Per-domain token bucket algorithm
- **Proxy Pool**: Rotation strategies (round_robin, random, least_used) with health tracking
- **Cookie Persistence**: Optional cookie storage between requests
- **Retry Logic**: Exponential backoff with configurable retry codes
- **Batch Operations**: `gather_sync()` and `gather_async()` for parallel requests

## Installation

```bash
pip install http-client

# Or with httpx fallback support
pip install http-client[httpx]

# Or for development
pip install http-client[dev]
```

## Quick Start

### Simple Sync Request

```python
from http_client import ScraperClient

client = ScraperClient()
response = client.get("https://example.com")
print(response.status_code)
print(response.text)
```

### Simple Async Request

```python
import asyncio
from http_client import ScraperClient

async def main():
    async with ScraperClient() as client:
        response = await client.get_async("https://example.com")
        print(response.text)

asyncio.run(main())
```

### Batch Operations

```python
# Thread pool batch (sync)
with ScraperClient(max_workers=20) as client:
    urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
    results = client.gather_sync(urls)

    for i, response in enumerate(results.responses):
        if response:
            print(f"URL {i}: {response.status_code}")

    # Check for errors
    if results.errors:
        print(f"Errors: {results.errors}")

# Async batch with concurrency control
async with ScraperClient() as client:
    results = await client.gather_async(urls, concurrency=50)
```

### Stealth Mode with Cookies and Proxies

```python
client = ScraperClient(
    mode="stealth",
    persist_cookies=True,
    profile="chrome_120",
    proxies=[
        "socks5://proxy1:1080",
        "http://user:pass@proxy2:8080",
    ],
    proxy_strategy="round_robin",
    rate_limit=2.0,  # 2 requests per second per domain
    min_delay=1.0,   # Random delay between 1-3 seconds
    max_delay=3.0,
)

# First request sets cookies
response = client.get("https://example.com/login")

# Subsequent requests automatically include cookies
response = client.get("https://example.com/dashboard")
```

### Speed Mode (No Frills)

```python
client = ScraperClient(
    mode="speed",
    rate_limit=0,  # Disable rate limiting
    retries=1,
    max_workers=50,
)

# Maximum throughput
results = client.gather_sync(urls)
```

## Configuration

```python
from http_client import ScraperClient, ClientConfig

# Using kwargs
client = ScraperClient(
    mode="stealth",           # "speed" or "stealth"
    persist_cookies=True,     # Enable cookie persistence
    profile="chrome_120",     # Browser profile for fingerprinting
    rate_limit=2.0,           # Requests/second per domain (0 to disable)
    timeout=30.0,             # Request timeout
    connect_timeout=10.0,     # Connection timeout
    retries=3,                # Retry attempts
    retry_codes=(429, 500, 502, 503, 504),
    retry_backoff_base=2.0,   # Exponential backoff base
    proxies=["socks5://..."], # Proxy URLs
    proxy_strategy="round_robin",  # "round_robin", "random", "least_used"
    proxy_max_failures=3,     # Failures before disabling proxy
    max_workers=10,           # Thread pool size
    default_concurrency=10,   # Async semaphore limit
    min_delay=1.0,            # Stealth mode min delay
    max_delay=3.0,            # Stealth mode max delay
    verify_ssl=True,          # SSL verification
    follow_redirects=True,    # Follow HTTP redirects
)

# Or using ClientConfig
config = ClientConfig(
    mode="stealth",
    persist_cookies=True,
    # ... other options
)
client = ScraperClient(config=config)
```

## Browser Profiles

Available profiles for TLS fingerprinting:

- Chrome: `chrome_120`, `chrome_119`, `chrome_118`
- Firefox: `firefox_121`, `firefox_120`, `firefox_117`
- Safari: `safari_17`, `safari_16`, `safari_15`
- Edge: `edge_120`, `edge_119`

```python
from http_client import get_profile, PROFILES

# Get a specific profile
profile = get_profile("chrome_120")
print(profile.user_agent)
print(profile.header_order)

# List all available profiles
print(list(PROFILES.keys()))
```

## Error Handling

```python
from http_client import (
    ScraperClient,
    TransportError,
    HTTPError,
    MaxRetriesExceeded,
    AllProxiesFailed,
)

client = ScraperClient()

try:
    response = client.get("https://example.com")
    response.raise_for_status()  # Raises HTTPError for 4xx/5xx
except TransportError as e:
    print(f"Connection error: {e}")
except HTTPError as e:
    print(f"HTTP error: {e.response.status_code}")
except MaxRetriesExceeded as e:
    print(f"Max retries exceeded for {e.url}")
except AllProxiesFailed:
    print("All proxies failed")
```

## Cookie Persistence

By default, cookies are NOT persisted between requests (stateless):

```python
# Default: stateless
client = ScraperClient()  # persist_cookies=False

# Response cookies are returned but not stored
response = client.get("https://example.com/login")
print(response.cookies)  # Shows cookies from this response

# Next request starts fresh - no cookies sent
response = client.get("https://example.com/dashboard")
```

To enable cookie persistence:

```python
client = ScraperClient(persist_cookies=True)

# Cookies are automatically stored and sent
response = client.get("https://example.com/login")
response = client.get("https://example.com/dashboard")  # Cookies included

# Access cookie store directly
if client.cookie_store:
    all_cookies = client.cookie_store.get_all()
    client.cookie_store.clear_all()
```

## Proxy Pool

```python
client = ScraperClient(
    proxies=[
        "http://proxy1:8080",
        "socks5://proxy2:1080",
        "http://user:pass@proxy3:8080",
    ],
    proxy_strategy="round_robin",  # or "random", "least_used"
    proxy_max_failures=3,          # Disable after 3 consecutive failures
    proxy_cooldown=300.0,          # Re-enable after 5 minutes
)

# Access proxy pool directly
if client.proxy_pool:
    stats = client.proxy_pool.get_stats()
    print(f"Available: {stats['available']}/{stats['total']}")

    # Force enable/disable
    client.proxy_pool.force_disable("http://proxy1:8080")
    client.proxy_pool.reset_all()
```

## Rate Limiting

```python
client = ScraperClient(rate_limit=2.0)  # 2 req/sec per domain

# Access rate limiter directly
if client.rate_limiter:
    # Set custom rate for specific domain
    client.rate_limiter.set_domain_rate("api.example.com", 10.0)

    # Get info
    info = client.rate_limiter.get_domain_info("https://example.com/path")
    print(f"Rate: {info['rate']} req/sec")
```

## Package Structure

```
http_client/
├── __init__.py              # Public API exports
├── client.py                # ScraperClient - unified interface
├── config.py                # ClientConfig dataclass
├── models.py                # Request, Response, exceptions
│
├── backends/
│   ├── base.py              # Abstract Backend protocol
│   ├── async_backend.py     # asyncio implementation
│   └── thread_backend.py    # ThreadPoolExecutor implementation
│
├── transport/
│   ├── base.py              # Transport protocol
│   └── curl_transport.py    # curl_cffi wrapper with httpx fallback
│
├── safety/
│   ├── rate_limiter.py      # Token bucket rate limiter
│   ├── proxy_pool.py        # Proxy pool with health tracking
│   └── cookie_store.py      # Thread+async safe cookie storage
│
└── fingerprint/
    ├── profiles.py          # Browser profile definitions
    └── headers.py           # Header generation and ordering
```

## Feature Summary

| Feature | Implementation |
|---------|---------------|
| **Dual Execution** | `gather_sync()` (ThreadPoolExecutor) and `gather_async()` (asyncio + semaphore) |
| **TLS Fingerprinting** | curl_cffi with browser impersonation, httpx fallback |
| **Thread Safety** | Dual-lock pattern (`threading.Lock` + `asyncio.Lock`) |
| **Rate Limiting** | Per-domain token bucket algorithm |
| **Proxy Pool** | Round-robin, random, least_used strategies with health tracking |
| **Cookie Persistence** | Opt-in via `persist_cookies=True` |
| **Retry Logic** | Exponential backoff, configurable status codes |
| **Speed/Stealth Modes** | Configurable behavior for different scraping needs |

## Dependencies

- **Required**: `curl_cffi>=0.5.0` - TLS fingerprinting
- **Optional**: `httpx>=0.25.0` - Fallback transport if curl_cffi unavailable

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/iampramodphuyal/http-client.git
cd http-client

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=http_client --cov-report=html

# Run specific test file
pytest tests/test_rate_limiter.py

# Run with verbose output
pytest -v

# Run async tests only
pytest -k "async"
```

### Code Quality

```bash
# Type checking
mypy http_client

# Linting
ruff check http_client

# Format code
ruff format http_client
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_config.py           # ClientConfig tests
├── test_models.py           # Request/Response tests
├── test_rate_limiter.py     # Rate limiter tests
├── test_proxy_pool.py       # Proxy pool tests
├── test_cookie_store.py     # Cookie store tests
├── test_fingerprint.py      # Browser profile tests
├── test_transport.py        # Transport layer tests
└── test_client.py           # Integration tests
```

## License

MIT License
