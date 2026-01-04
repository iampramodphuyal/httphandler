# Changelog

All notable changes to this project will be documented in this file.

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
