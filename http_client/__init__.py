"""HTTP client package for web scraping with dual execution model support.

This package provides a unified HTTP client interface supporting both
asyncio and ThreadPoolExecutor execution models with:

- TLS fingerprint impersonation via curl_cffi
- Thread-safe and async-safe rate limiting
- Proxy pool with rotation strategies and health tracking
- Optional cookie persistence
- Retry logic with exponential backoff
- Two operating modes: "speed" and "stealth"

Basic usage:

    # Simple sync request
    from http_client import ScraperClient

    client = ScraperClient()
    response = client.get("https://example.com")
    print(response.text)

    # Simple async request
    async with ScraperClient() as client:
        response = await client.get_async("https://example.com")
        print(response.text)

    # Batch operations
    with ScraperClient(max_workers=20) as client:
        results = client.gather_sync(["https://example.com/1", "https://example.com/2"])

    async with ScraperClient() as client:
        results = await client.gather_async(urls, concurrency=50)

    # Stealth mode with cookies and proxies
    client = ScraperClient(
        mode="stealth",
        persist_cookies=True,
        profile="chrome_120",
        proxies=["socks5://proxy1:1080"],
    )
"""

from .client import ScraperClient
from .config import ClientConfig
from .models import (
    Request,
    Response,
    BatchResult,
    HTTPClientError,
    TransportError,
    HTTPError,
    RateLimitExceeded,
    AllProxiesFailed,
    MaxRetriesExceeded,
)
from .fingerprint import (
    BrowserProfile,
    PROFILES,
    get_profile,
    HeaderGenerator,
)
from .safety import (
    TokenBucket,
    DomainRateLimiter,
    Proxy,
    ProxyPool,
    CookieStore,
)

__version__ = "0.1.0"

__all__ = [
    # Main client
    "ScraperClient",
    # Configuration
    "ClientConfig",
    # Models
    "Request",
    "Response",
    "BatchResult",
    # Exceptions
    "HTTPClientError",
    "TransportError",
    "HTTPError",
    "RateLimitExceeded",
    "AllProxiesFailed",
    "MaxRetriesExceeded",
    # Fingerprinting
    "BrowserProfile",
    "PROFILES",
    "get_profile",
    "HeaderGenerator",
    # Safety primitives
    "TokenBucket",
    "DomainRateLimiter",
    "Proxy",
    "ProxyPool",
    "CookieStore",
    # Version
    "__version__",
]
