# Changelog

All notable changes to this project will be documented in this file.

## [0.5.7] - 2026-01-08

### Added
- Modular proxy management system with provider abstraction (`_proxy/` module)
- `ProxyManager` class with round-robin rotation and health tracking
- `GenericProvider` for custom proxy URLs with country/type filtering
- Abstract `ProxyProvider` base class for extending with custom providers
- New proxy methods: `set_proxy()`, `reset_proxy()`, `switch_proxy()`, `get_current_proxy()`
- Async variants: `set_proxy_async()`, `reset_proxy_async()`, `switch_proxy_async()`, `get_current_proxy_async()`
- Proxy health tracking with auto-failover (3 failures = 60s cooldown)
- `ProxyConfig`, `ProxyHealth`, `ProxyPoolStats` data models
- `ProxyError` exception hierarchy
- Comprehensive test suite for proxy module (63 tests)

### Changed
- `set_proxy()` now supports multiple signatures: URL string, proxies list, or provider-based
- Backward compatible with existing `set_proxy("http://proxy:8080")` usage
- Updated README with proxy management documentation
- Updated CLAUDE.md with proxy module architecture

## [0.5.6] - 2026-01-05

### Added
- HTTP version configuration (`http_version` parameter) for both httpx and curl backends
- Supports "1.1", "2", or None (auto) for HTTP version selection

## [0.5.5] - 2026-01-05

### Added
- Stealth mode (`stealth=True`) now works with httpx backend using browserforge headers
- Full request details (headers, json, params, data, cookies) now stored in `Response.request`

### Fixed
- Fixed browserforge API compatibility (handles both old object API and new dict API)
- Fixed browserforge `os=None` parameter bug causing TypeError

### Changed
- Updated README with stealth mode comparison table
- httpx backend now accepts `profile` parameter for header generation

## [0.5.4] - 2026-01-05

### Fixed
- Fixed cookie storage bug where empty CookieStore's `__bool__` returned False, preventing cookies from being stored on first request

### Changed
- Updated test suite for the new HTTPClient API
- Removed obsolete test files (test_config.py, test_transport.py, test_rate_limiter.py, test_proxy_pool.py, test_handler.py)

## [0.5.3] - 2025-01-04

### Fixed
- Fixed HTTP/2 dependency (changed to `httpx[http2]>=0.25.0`)
- Added error handling fallback for browserforge header generation
- Fixed elapsed time handling for curl_cffi timedelta objects

## [0.5.2] - 2025-01-04

### Changed
- Updated CLAUDE.md with development commands and concise architecture

## [0.5.1] - 2025-01-04

### Changed
- Made httpx, curl_cffi, and browserforge required dependencies (no longer optional)

## [0.5.0] - 2025-01-04

### Added
- New unified `HTTPClient` API with per-request backend switching
- Browserforge integration for realistic browser headers in stealth mode
- Shared cookie persistence across httpx and curl backends

### Changed
- Replaced `ScraperClient` with simplified `HTTPClient`
- Removed complex features (rate limiting, proxy pools, batch operations) for cleaner API

## [0.4.0] - Previous

- Initial ScraperClient implementation with dual execution model
