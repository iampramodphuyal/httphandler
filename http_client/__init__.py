"""HTTP client package for web scraping with dual execution model support.

This package provides two interfaces:

1. **HTTPHandler** (Simple) - For straightforward HTTP requests:
   - Session persistence control
   - Response helper methods
   - Header and proxy management
   - Streaming support

2. **ScraperClient** (Advanced) - For complex scraping needs:
   - TLS fingerprint impersonation via curl_cffi
   - Thread-safe and async-safe rate limiting
   - Proxy pool with rotation strategies
   - Browser profile emulation

Simple usage (HTTPHandler):

    from http_client import HTTPHandler

    handler = HTTPHandler()
    resp = handler.get("https://example.com", headers={"User-Agent": "MyApp/1.0"})
    print(handler.get_status_code())
    print(handler.get_cookies())

    # Session management
    handler.persist_session = True
    handler.get("https://example.com/login")
    handler.get("https://example.com/dashboard")  # Cookies maintained
    handler.reset_session()  # Clear for new session

Advanced usage (ScraperClient):

    from http_client import ScraperClient

    # Stealth mode with cookies and proxies
    client = ScraperClient(
        mode="stealth",
        persist_cookies=True,
        profile="chrome_120",
        proxies=["socks5://proxy1:1080"],
    )
    response = client.get("https://example.com")

    # Batch operations
    async with ScraperClient() as client:
        results = await client.gather_async(urls, concurrency=50)
"""

from .client import ScraperClient
from .config import ClientConfig
from .handler import HTTPHandler, NoResponseError
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
    # Simple interface
    "HTTPHandler",
    # Advanced interface
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
    "NoResponseError",
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
