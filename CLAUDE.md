# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run single test file
pytest tests/test_client.py

# Run specific test
pytest tests/test_client.py::test_get_request -v

# Type checking
mypy http_client

# Linting
ruff check http_client
ruff format http_client
```

## Architecture

Unified Python HTTP client with per-request backend switching between httpx and curl_cffi, sharing session state (cookies) across backends.

```
http_client/
├── __init__.py          # Public API: HTTPClient, Response, exceptions
├── client.py            # Unified HTTPClient class
├── models.py            # Request, Response, exception classes
├── _backends/           # Backend implementations
│   ├── httpx_backend.py # httpx wrapper (sync + async)
│   └── curl_backend.py  # curl_cffi wrapper with stealth/fingerprinting
├── _cookies.py          # Thread-safe + async-safe cookie storage (dual-lock pattern)
└── _fingerprint/        # Browser profiles for stealth mode
    ├── profiles.py      # Browser profile definitions (Chrome, Firefox, Safari, Edge)
    ├── headers.py       # Header generation and ordering
    └── browserforge_adapter.py  # Browserforge integration for realistic headers
```

## Key Design Patterns

### Per-Request Backend Switching
```python
client = HTTPClient(persist_cookies=True)
resp1 = client.get(url, backend="httpx")       # Fast, default
resp2 = client.get(url, backend="curl", stealth=True)  # TLS fingerprinting
# Cookies shared between both requests
```

### Cookie Sharing via CookieStore
Single `CookieStore` instance shared across backends. Uses dual-lock pattern:
- `threading.Lock` for thread safety
- `asyncio.Lock` (lazy-initialized) for async safety

### Stealth Mode (curl backend only)
When `stealth=True`:
- Browserforge generates realistic headers (with fallback to static profiles)
- Custom headers override generated headers
- TLS fingerprinting via curl_cffi's `impersonate` parameter

### Lazy Backend Initialization
Backends created only when first used via `_get_httpx_backend()` / `_get_curl_backend()`.

## Core Principles

1. **httpx is default** - curl_cffi only when `backend="curl"`
2. **Explicit over implicit** - Cookies don't persist unless `persist_cookies=True`
3. **Custom headers win** - User headers always override generated/default headers
