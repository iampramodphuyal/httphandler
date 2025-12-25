# HTTP Client Package for Web Scraping Framework

## Project Overview
A Python HTTP client package designed for web scraping, supporting both asyncio and thread pool execution models with TLS fingerprinting, stealth capabilities, and robust safety guarantees.

## Core Design Principles

### 1. Dual Execution Model Safety
Every shared component must be safe for concurrent access from both asyncio tasks and thread pool workers. Use dual-lock pattern where necessary:
- `threading.Lock` for thread safety
- `asyncio.Lock` for async safety (lazy-initialized within event loop)

### 2. Explicit Over Implicit
- Cookies/sessions do NOT persist by default
- Persistence only when `persist_cookies=True` at initialization
- No hidden state that surprises the user

### 3. Speed vs Stealth Trade-off
Two distinct modes with clear behavioral differences. User chooses based on target site requirements.

## Architecture
```
http_client/
├── __init__.py              # Public API exports
├── client.py                # ScraperClient - unified interface
├── config.py                # ClientConfig dataclass, mode enums
├── models.py                # Request, Response dataclasses
│
├── backends/
│   ├── base.py              # Abstract Backend protocol
│   ├── async_backend.py     # asyncio implementation
│   └── thread_backend.py    # sync/thread implementation
│
├── transport/
│   ├── base.py              # Transport protocol
│   └── curl_transport.py    # curl_cffi wrapper with fingerprinting
│
├── safety/
│   ├── rate_limiter.py      # TokenBucket, DomainRateLimiter
│   ├── proxy_pool.py        # ProxyPool with health tracking
│   └── cookie_store.py      # Thread+async safe cookie storage
│
└── fingerprint/
    ├── profiles.py          # Browser profile definitions
    └── headers.py           # Header sets and ordering
```

## Key Implementation Details

### Session/Cookie Behavior
```python
# Default: stateless, no cookie persistence
client = ScraperClient()

# Explicit opt-in for cookie persistence
client = ScraperClient(persist_cookies=True)
```

When `persist_cookies=False` (default):
- Each request starts with empty cookie jar
- Response cookies are returned but not stored
- Manual cookie injection still works via `cookies` parameter

When `persist_cookies=True`:
- CookieStore initialized and shared across requests
- Cookies accumulated and sent on subsequent requests to same domain
- Thread-safe and async-safe access to cookie store

### Rate Limiter Implementation
Use token bucket algorithm with dual-lock pattern:
- `acquire_sync()` - blocking, uses threading.Lock + time.sleep
- `acquire_async()` - non-blocking, uses asyncio.Lock + asyncio.sleep
- Per-domain buckets stored in dict, bucket creation protected by lock

### Proxy Pool Implementation
- List of Proxy objects with health metadata
- `threading.Lock` protects all reads and mutations
- Strategies: round_robin (default), random, least_recently_used
- Auto-disable after `max_failures` consecutive failures
- Track `last_used` timestamp for least_recently_used strategy

### Transport Layer (curl_cffi)
- Wrap `curl_cffi.requests.Session` for sync
- Wrap `curl_cffi.requests.AsyncSession` for async
- Pass `impersonate` parameter for TLS fingerprinting
- Configure header order via profile

## Browser Profiles
Define profiles as dataclasses containing:
- `impersonate`: curl_cffi impersonate string (e.g., "chrome120")
- `headers`: ordered dict of default headers
- `header_order`: list defining header transmission order
- `tls_config`: any additional TLS settings

Provide presets: CHROME_120, CHROME_119, FIREFOX_121, SAFARI_17, etc.

## Configuration Options
```python
@dataclass
class ClientConfig:
    # Execution
    mode: Literal["speed", "stealth"] = "speed"
    
    # Session
    persist_cookies: bool = False
    
    # Fingerprinting
    profile: str = "chrome_120"
    
    # Rate limiting
    rate_limit: float = 2.0  # req/sec per domain
    
    # Timeouts
    timeout: float = 30.0
    connect_timeout: float = 10.0
    
    # Retries
    retries: int = 3
    retry_codes: tuple[int, ...] = (429, 500, 502, 503, 504, 520, 521, 522, 523, 524)
    retry_backoff_base: float = 2.0
    
    # Proxies
    proxies: list[str] | None = None
    proxy_strategy: Literal["round_robin", "random", "least_used"] = "round_robin"
    proxy_max_failures: int = 3
    
    # Thread pool (for gather_sync)
    max_workers: int = 10
    
    # Async (for gather_async)
    default_concurrency: int = 10
    
    # Stealth mode specific
    min_delay: float = 1.0  # random delay range
    max_delay: float = 3.0
```

## Error Handling
- Define custom exceptions: `TransportError`, `RateLimitExceeded`, `AllProxiesFailed`
- Batch operations capture exceptions per-request, optionally stop on first error
- Retry logic catches connection errors and configurable status codes

## Testing Approach
- Unit tests for safety primitives (rate limiter, proxy pool, cookie store)
- Test concurrent access from multiple threads
- Test concurrent access from multiple async tasks
- Integration tests against httpbin or similar

## Dependencies
- `curl_cffi` - TLS fingerprinting, HTTP transport
- `httpx` - fallback transport (optional)
- Standard library: asyncio, threading, concurrent.futures, dataclasses, time, urllib.parse

## Usage Patterns to Support
```python
# Simple sync
client = ScraperClient()
resp = client.get(url)

# Simple async
async with ScraperClient() as client:
    resp = await client.get_async(url)

# Thread pool batch
with ScraperClient(max_workers=20) as client:
    results = client.gather_sync(urls)

# Async batch with concurrency
async with ScraperClient() as client:
    results = await client.gather_async(urls, concurrency=50)

# Stealth with cookies
client = ScraperClient(
    mode="stealth",
    persist_cookies=True,
    profile="chrome_120",
    proxies=["socks5://..."],
)

# Speed mode, no frills
client = ScraperClient(mode="speed", rate_limit=0)  # 0 = no limit
```
