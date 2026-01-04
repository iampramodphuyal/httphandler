# HTTP Client Package

## Project Overview

A unified Python HTTP client with per-request backend switching between httpx and curl_cffi. Features shared cookie persistence across backends, optional browser fingerprinting for stealth mode, and both sync/async support.

## Core Design Principles

### 1. Unified API with Per-Request Backend Switching

Single `HTTPClient` class that supports switching between httpx and curl backends on each request while sharing session state (cookies).

```python
client = HTTPClient(persist_cookies=True)
resp1 = client.get("https://api.example.com", backend="httpx")
resp2 = client.get("https://protected.com", backend="curl", stealth=True)
# Cookies shared between requests!
```

### 2. httpx as Default Backend

- httpx is the default for speed and reliability
- curl_cffi used when `backend="curl"` is specified
- Stealth features only apply with `backend="curl"` and `stealth=True`

### 3. Explicit Over Implicit

- Cookies do NOT persist by default
- Persistence only when `persist_cookies=True` at initialization
- Stealth mode requires explicit `stealth=True` parameter

## Architecture

```
http_client/
├── __init__.py              # Public API: HTTPClient, Response, exceptions
├── client.py                # Unified HTTPClient class
├── models.py                # Request, Response, exceptions
│
├── _backends/               # Internal backend implementations
│   ├── __init__.py
│   ├── httpx_backend.py     # httpx wrapper (sync + async)
│   └── curl_backend.py      # curl_cffi wrapper with stealth
│
├── _cookies.py              # Thread-safe + async-safe cookie storage
│
└── _fingerprint/            # Browser profiles for stealth mode
    ├── __init__.py
    ├── profiles.py          # Browser profile definitions
    ├── headers.py           # Header generation and ordering
    └── browserforge_adapter.py
```

## Key Implementation Details

### HTTPClient Class

The main interface supporting both backends:

```python
class HTTPClient:
    def __init__(
        self,
        default_backend: Literal["httpx", "curl"] = "httpx",
        persist_cookies: bool = False,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        verify_ssl: bool = True,
        proxy: str | None = None,
        follow_redirects: bool = True,
        profile: str = "chrome_120",  # For curl stealth mode
    ):
        ...
```

### Cookie Sharing Strategy

The `CookieStore` is the single source of truth shared across both backends:

```python
def request(self, method, url, *, cookies=None, backend=None, ...):
    # 1. Get stored cookies + merge with request cookies
    final_cookies = {}
    if self._cookie_store:
        final_cookies.update(self._cookie_store.get_for_url(url))
    if cookies:
        final_cookies.update(cookies)

    # 2. Execute request with chosen backend
    if backend == "curl":
        response = self._curl_backend.request_sync(..., cookies=final_cookies)
    else:
        response = self._httpx_backend.request_sync(..., cookies=final_cookies)

    # 3. Store response cookies
    if self._cookie_store and response.cookies:
        self._cookie_store.update_from_response(url, response.cookies)

    return response
```

### Backend Selection

Per-request backend selection with default fallback:

```python
def _resolve_backend(self, backend: str | None) -> str:
    return backend or self._default_backend
```

### Lazy Backend Initialization

Backends are created only when first used:

```python
def _get_httpx_backend(self) -> HttpxBackend:
    if self._httpx_backend is None:
        self._httpx_backend = HttpxBackend(...)
    return self._httpx_backend

def _get_curl_backend(self) -> CurlBackend:
    if self._curl_backend is None:
        self._curl_backend = CurlBackend(...)
    return self._curl_backend
```

### Helper Methods

Access last response state without storing response separately:

```python
def get_status_code(self) -> int | None:
    return self._last_response.status_code if self._last_response else None

def get_headers(self) -> dict[str, str] | None:
    return dict(self._last_response.headers) if self._last_response else None

def get_cookies(self) -> dict[str, str] | None:
    return dict(self._last_response.cookies) if self._last_response else None

def get_current_proxy(self) -> str | None:
    return self._proxy

def get_elapsed(self) -> float | None:
    return self._last_response.elapsed if self._last_response else None
```

## Backend Implementations

### HttpxBackend

Simple wrapper around httpx:

```python
class HttpxBackend:
    def request_sync(self, method, url, headers, params, data, json,
                     cookies, timeout, proxy) -> Response
    async def request_async(...) -> Response
    def close_sync() / async def close_async()
```

### CurlBackend

curl_cffi wrapper with stealth features:

```python
class CurlBackend:
    def request_sync(self, method, url, headers, params, data, json,
                     cookies, timeout, proxy, stealth=False) -> Response
    async def request_async(...) -> Response
    def close_sync() / async def close_async()
```

When `stealth=True`:
- Generates realistic browser headers via browserforge (if installed) or static profiles
- Custom headers override generated headers (custom takes precedence)
- Uses TLS fingerprinting via curl_cffi's `impersonate` parameter
- Orders headers according to browser profile

When `stealth=False`:
- Only uses custom headers provided by user (or empty)

## CookieStore (Dual-Lock Pattern)

Thread-safe and async-safe cookie storage:

```python
class CookieStore:
    def __init__(self):
        self._cookies: dict[str, dict[str, Cookie]] = {}
        self._thread_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None  # Lazy initialized

    def get_for_url(self, url: str) -> dict[str, str]:
        # Thread-safe cookie retrieval
        ...

    async def get_for_url_async(self, url: str) -> dict[str, str]:
        # Async-safe cookie retrieval
        ...

    def update_from_response(self, url: str, cookies: dict[str, str]) -> None:
        # Thread-safe cookie storage
        ...

    async def update_from_response_async(self, url: str, cookies: dict[str, str]) -> None:
        # Async-safe cookie storage
        ...
```

## Browser Profiles

Predefined profiles for TLS fingerprinting:

- Chrome: `chrome_120`, `chrome_119`, `chrome_118`
- Firefox: `firefox_121`, `firefox_120`, `firefox_117`
- Safari: `safari_17`, `safari_16`, `safari_15`
- Edge: `edge_120`, `edge_119`

Each profile includes:
- `impersonate`: curl_cffi impersonate string
- `user_agent`: User-Agent header value
- `header_order`: Header transmission order
- `sec_ch_ua`, `sec_ch_ua_mobile`, `sec_ch_ua_platform`: Chrome client hints

## Error Handling

Custom exceptions:
- `HTTPClientError`: Base exception
- `TransportError`: Connection/timeout errors
- `HTTPError`: 4xx/5xx responses
- `MaxRetriesExceeded`: Retries exhausted

## Dependencies

Required:
- `httpx` - Default HTTP backend

Optional:
- `curl_cffi` - TLS fingerprinting, stealth mode

Standard library:
- `asyncio`, `threading`, `dataclasses`, `urllib.parse`

## Usage Patterns

```python
# Simple usage (httpx default)
client = HTTPClient()
resp = client.get(url)

# With cookie persistence
client = HTTPClient(persist_cookies=True)
client.post("https://example.com/login", json={"user": "..."})
client.get("https://example.com/dashboard")  # Cookies sent

# Per-request backend switching
resp1 = client.get(url, backend="httpx")
resp2 = client.get(url, backend="curl", stealth=True)

# Async usage
async with HTTPClient() as client:
    resp = await client.get_async(url)

# Helper methods
client.get(url)
print(client.get_status_code())
print(client.get_headers())
print(client.get_cookies())
```
