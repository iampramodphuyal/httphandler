Create an HTTP client package for a web scraping framework with the following requirements:

## Core Execution Model
- Must support both asyncio (async/await) and ThreadPoolExecutor execution models
- All shared state (rate limiters, proxy pools, cookie stores) must be safe for concurrent access in both models
- User can use sync methods, async methods, or both within the same application
- Provide batch operations for both models: gather_sync (thread pool) and gather_async (asyncio with semaphore)

## HTTP Transport
- Use curl_cffi as primary transport for TLS fingerprint impersonation
- Support browser impersonation profiles: Chrome, Firefox, Safari (various versions)
- Control header ordering to match browser fingerprints
- Fallback to httpx if curl_cffi unavailable

## Two Operating Modes
1. Speed Mode: No artificial delays, aggressive connection pooling, minimal headers, skip fingerprint spoofing, max concurrency
2. Stealth Mode: Random delays between requests, browser-like TLS fingerprint, full realistic headers with proper ordering, optional proxy rotation, referer chain building

## Session and Cookie Handling
- By default: NO cookie persistence between requests (stateless)
- Cookies/sessions only persist when explicitly enabled via parameter at client initialization (e.g., `persist_cookies=True` or `session_mode=True`)
- When enabled: cookie store must be thread-safe and async-safe
- Support manual cookie injection regardless of persistence setting

## Rate Limiting
- Per-domain token bucket rate limiter
- Must work correctly under both async and threaded execution
- Configurable rate per domain or global default

## Proxy Support
- Proxy pool with rotation strategies: round_robin, random, least_recently_used
- Health tracking: disable proxies after N consecutive failures
- Auto-recovery: re-enable proxies after cooldown period
- Thread-safe proxy selection

## Retry Logic
- Configurable retry count
- Exponential backoff
- Configurable retry status codes (default: 429, 500, 502, 503, 504, 520-524)
- Proxy failover on connection errors

## API Design
- Single ScraperClient class with unified interface
- Sync methods: get(), post(), request(), gather_sync()
- Async methods: get_async(), post_async(), request_async(), gather_async()
- Context manager support for both sync and async
- Configuration via dataclass or kwargs

## Safety Requirements
- All shared mutable state protected by appropriate locks
- Dual-lock pattern where needed (threading.Lock + asyncio.Lock)
- Graceful shutdown with resource cleanup
- Exception isolation in batch operations (configurable)
- No global mutable state

## Package Structure
Organize as installable package with clear separation:
- Client interface
- Backends (async, thread)
- Transport layer (curl_cffi wrapper)
- Safety primitives (rate limiter, proxy pool, cookie store)
- Fingerprint profiles
- Models (Request, Response dataclasses)
