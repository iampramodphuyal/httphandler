# HTTP Client

A Python HTTP client package for web scraping and API interactions, featuring two interfaces: a simple `HTTPHandler` for beginners and an advanced `ScraperClient` for complex scraping with TLS fingerprinting and stealth capabilities.

## Features

### Simple Interface (HTTPHandler)
- Clean, intuitive API for HTTP requests
- Session persistence with `persist_session` flag
- Response helpers: `get_status_code()`, `get_cookies()`, `get_headers()`, `get_bandwidth()`
- Header and proxy management
- Streaming downloads with progress callbacks
- Context managers for automatic cleanup

### Advanced Interface (ScraperClient)
- **Dual Execution Model**: asyncio and ThreadPoolExecutor support
- **TLS Fingerprinting**: Mimic real browsers (Chrome, Firefox, Safari, Edge)
- **Speed/Stealth Modes**: Optimized for different scraping scenarios
- **Thread-safe & Async-safe**: Protected rate limiters, proxy pools, cookies
- **Rate Limiting**: Per-domain token bucket algorithm
- **Proxy Pool**: Rotation strategies with health tracking
- **Batch Operations**: `gather_sync()` and `gather_async()`

## Installation

```bash
# Install latest version
pip install git+https://github.com/iampramodphuyal/httphandler.git

# Install specific version
pip install git+https://github.com/iampramodphuyal/httphandler.git@v0.3.0

# For development
git clone https://github.com/iampramodphuyal/httphandler.git
cd httphandler
pip install -e ".[dev]"
```

## Quick Start

### HTTPHandler (Simple - Recommended for Beginners)

```python
from http_client import HTTPHandler

# Create handler with default headers
handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})

# Make requests
response = handler.get("https://httpbin.org/get")
print(handler.get_status_code())  # 200
print(handler.get_cookies())      # {"session": "..."}
print(handler.get_headers())      # {"Content-Type": "..."}
print(handler.get_bandwidth())    # 1234.5 bytes/sec

# Session management
handler.persist_session = True
handler.post("https://example.com/login", data={"user": "john"})
handler.get("https://example.com/dashboard")  # Cookies included
handler.reset_session()  # Clear for fresh start

# Context manager
with HTTPHandler(headers={"User-Agent": "MyApp/1.0"}) as h:
    h.get("https://example.com")
# Auto-cleanup
```

### ScraperClient (Advanced)

```python
from http_client import ScraperClient

# Simple request
client = ScraperClient()
response = client.get("https://example.com")
print(response.text)
client.close()

# Async request
import asyncio

async def main():
    async with ScraperClient() as client:
        response = await client.get_async("https://example.com")
        print(response.text)

asyncio.run(main())

# Stealth mode with all features
client = ScraperClient(
    mode="stealth",
    persist_cookies=True,
    profile="chrome_120",
    proxies=["socks5://proxy1:1080", "http://proxy2:8080"],
    proxy_strategy="round_robin",
    rate_limit=2.0,
    min_delay=1.0,
    max_delay=3.0,
)
```

## HTTPHandler Features

### Response Helpers

```python
handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})
handler.get("https://httpbin.org/get")

# Access last response data
handler.get_status_code()     # HTTP status code
handler.get_cookies()         # Response cookies
handler.get_headers()         # Response headers
handler.get_bandwidth()       # bytes/second
handler.get_elapsed()         # Request duration
handler.get_content_length()  # Response size
handler.get_response()        # Full Response object
```

### Session Control

```python
handler = HTTPHandler(persist_session=True, headers={"User-Agent": "MyApp/1.0"})

# Requests 1-3: Same session (cookies maintained)
handler.get("https://example.com/step1")
handler.get("https://example.com/step2")
handler.get("https://example.com/step3")

# Reset for independent requests
handler.reset_session()

# Requests 4-5: Fresh session
handler.get("https://example.com/other1")
handler.get("https://example.com/other2")
```

### Header Management

```python
handler = HTTPHandler()

handler.set_headers({"User-Agent": "MyApp/1.0", "Accept": "application/json"})
handler.add_header("Authorization", "Bearer token123")
handler.remove_header("Accept")
handler.clear_headers()
```

### Proxy Control

```python
handler = HTTPHandler(proxy="socks5://localhost:1080")

handler.disable_proxy()  # Temporarily disable
handler.enable_proxy()   # Re-enable
handler.set_proxy("http://newproxy:8080")  # Change proxy
```

### Streaming Downloads

```python
handler = HTTPHandler(headers={"User-Agent": "Downloader/1.0"})

# With progress callback
def progress(chunk, downloaded, total):
    print(f"Downloaded: {downloaded}/{total}")

with open("file.zip", "wb") as f:
    for chunk in handler.stream("https://example.com/file.zip", callback=progress):
        f.write(chunk)
```

### Context Managers

```python
# Auto-cleanup on exit
with HTTPHandler(headers={"User-Agent": "MyApp/1.0"}) as handler:
    handler.get("https://example.com")

# Scoped session with auto-reset
handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})
with handler.session() as session:
    session.get("https://example.com/step1")
    session.get("https://example.com/step2")
# Session automatically reset here
```

## ScraperClient Features

### Batch Operations

```python
# Thread pool (sync)
with ScraperClient(max_workers=20) as client:
    urls = [f"https://example.com/{i}" for i in range(100)]
    results = client.gather_sync(urls)

    print(f"Success: {results.success_count}")
    print(f"Failed: {results.failure_count}")

# Async with concurrency control
async with ScraperClient() as client:
    results = await client.gather_async(urls, concurrency=50)
```

### Speed vs Stealth Modes

```python
# Speed mode: Maximum throughput
client = ScraperClient(
    mode="speed",
    rate_limit=0,
    max_workers=50,
)

# Stealth mode: Browser-like behavior
client = ScraperClient(
    mode="stealth",
    profile="chrome_120",
    persist_cookies=True,
    rate_limit=2.0,
    min_delay=1.0,
    max_delay=3.0,
)
```

### Browser Profiles

Available profiles for TLS fingerprinting:
- Chrome: `chrome_120`, `chrome_119`, `chrome_118`
- Firefox: `firefox_121`, `firefox_120`, `firefox_117`
- Safari: `safari_17`, `safari_16`, `safari_15`
- Edge: `edge_120`, `edge_119`

```python
from http_client import get_profile, PROFILES

profile = get_profile("chrome_120")
print(profile.user_agent)
print(list(PROFILES.keys()))
```

### Proxy Pool

```python
client = ScraperClient(
    proxies=[
        "http://proxy1:8080",
        "socks5://proxy2:1080",
        "http://user:pass@proxy3:8080",
    ],
    proxy_strategy="round_robin",  # or "random", "least_used"
    proxy_max_failures=3,
    proxy_cooldown=300.0,
)

# Check pool status
if client.proxy_pool:
    stats = client.proxy_pool.get_stats()
    print(f"Available: {stats['available']}/{stats['total']}")
```

### Rate Limiting

```python
client = ScraperClient(rate_limit=2.0)  # 2 req/sec per domain

if client.rate_limiter:
    client.rate_limiter.set_domain_rate("api.example.com", 10.0)
```

## Error Handling

```python
from http_client import (
    HTTPHandler,
    ScraperClient,
    TransportError,
    HTTPError,
    MaxRetriesExceeded,
    NoResponseError,
)

# HTTPHandler
handler = HTTPHandler(headers={"User-Agent": "MyApp/1.0"})
try:
    handler.get("https://example.com")
except TransportError as e:
    print(f"Connection error: {e}")

# Check for response before using helpers
try:
    print(handler.get_status_code())
except NoResponseError:
    print("No request made yet")

# ScraperClient
try:
    response = client.get("https://example.com")
    response.raise_for_status()
except HTTPError as e:
    print(f"HTTP error: {e.response.status_code}")
except MaxRetriesExceeded as e:
    print(f"Retries exhausted for {e.url}")
```

## Configuration Reference

### HTTPHandler Options

```python
HTTPHandler(
    persist_session=False,     # Cookie persistence
    timeout=30.0,              # Request timeout
    connect_timeout=10.0,      # Connection timeout
    verify_ssl=True,           # SSL verification
    http_version="auto",       # "1.1", "2", or "auto"
    proxy=None,                # Proxy URL
    max_retries=3,             # Retry attempts
    headers=None,              # Default headers
)
```

### ScraperClient Options

```python
ScraperClient(
    mode="speed",              # "speed" or "stealth"
    persist_cookies=False,     # Cookie persistence
    profile="chrome_120",      # Browser profile
    rate_limit=2.0,            # Requests/sec per domain
    timeout=30.0,              # Request timeout
    connect_timeout=10.0,      # Connection timeout
    retries=3,                 # Retry attempts
    proxies=None,              # List of proxy URLs
    proxy_strategy="round_robin",
    proxy_max_failures=3,
    proxy_cooldown=300.0,
    max_workers=10,            # Thread pool size
    default_concurrency=10,    # Async semaphore limit
    min_delay=1.0,             # Stealth mode delays
    max_delay=3.0,
    verify_ssl=True,
    follow_redirects=True,
    max_redirects=10,
    http_version="auto",
)
```

## Package Structure

```
http_client/
├── __init__.py              # Public API exports
├── client.py                # ScraperClient
├── handler.py               # HTTPHandler (simple interface)
├── config.py                # ClientConfig dataclass
├── models.py                # Request, Response, exceptions
├── backends/                # Async and thread backends
├── transport/               # curl_cffi transport with httpx fallback
├── safety/                  # Rate limiter, proxy pool, cookie store
└── fingerprint/             # Browser profiles and headers
```

## Thread Safety

All shared components are thread-safe and async-safe:
- Rate limiter uses dual-lock pattern
- Proxy pool protected by threading locks
- Cookie store safe for concurrent access

```python
from concurrent.futures import ThreadPoolExecutor

client = ScraperClient(rate_limit=2.0)

def fetch(url):
    return client.get(url).status_code

with client:
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch, urls))
```

## Development

```bash
# Setup
git clone https://github.com/iampramodphuyal/httphandler.git
cd httphandler
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=http_client

# Type checking
mypy http_client

# Linting
ruff check http_client
```

## Documentation

See [USAGE.md](USAGE.md) for comprehensive documentation including:
- Complete HTTPHandler guide
- Advanced ScraperClient features
- Async and thread pool operations
- Thread safety patterns
- Real-world examples
- Troubleshooting

## License

MIT License
