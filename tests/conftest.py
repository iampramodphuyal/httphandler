"""Shared test fixtures and configuration."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from http_client import (
    ClientConfig,
    CookieStore,
    DomainRateLimiter,
    ProxyPool,
    Request,
    Response,
    ScraperClient,
)
from http_client.transport import CurlTransport


# ============== Configuration Fixtures ==============

@pytest.fixture
def default_config() -> ClientConfig:
    """Default client configuration."""
    return ClientConfig()


@pytest.fixture
def stealth_config() -> ClientConfig:
    """Stealth mode configuration."""
    return ClientConfig(
        mode="stealth",
        persist_cookies=True,
        profile="chrome_120",
        rate_limit=2.0,
        min_delay=0.1,  # Reduced for faster tests
        max_delay=0.2,
    )


@pytest.fixture
def speed_config() -> ClientConfig:
    """Speed mode configuration."""
    return ClientConfig(
        mode="speed",
        rate_limit=0,
        retries=1,
        max_workers=5,
    )


@pytest.fixture
def config_with_proxies() -> ClientConfig:
    """Configuration with proxies."""
    return ClientConfig(
        proxies=[
            "http://proxy1:8080",
            "http://proxy2:8080",
            "socks5://proxy3:1080",
        ],
        proxy_strategy="round_robin",
        proxy_max_failures=2,
        proxy_cooldown=10.0,
    )


# ============== Safety Primitive Fixtures ==============

@pytest.fixture
def rate_limiter() -> DomainRateLimiter:
    """Domain rate limiter with 10 req/sec."""
    return DomainRateLimiter(default_rate=10.0)


@pytest.fixture
def slow_rate_limiter() -> DomainRateLimiter:
    """Slow rate limiter for testing delays."""
    return DomainRateLimiter(default_rate=2.0)


@pytest.fixture
def proxy_pool() -> ProxyPool:
    """Proxy pool with test proxies."""
    return ProxyPool(
        proxies=[
            "http://proxy1:8080",
            "http://proxy2:8080",
            "http://proxy3:8080",
        ],
        strategy="round_robin",
        max_failures=2,
        cooldown=10.0,
    )


@pytest.fixture
def cookie_store() -> CookieStore:
    """Empty cookie store."""
    return CookieStore()


@pytest.fixture
def populated_cookie_store() -> CookieStore:
    """Cookie store with test cookies."""
    store = CookieStore()
    store.set("session_id", "abc123", domain="example.com")
    store.set("user_token", "xyz789", domain="example.com", path="/api")
    store.set("other_cookie", "value", domain="other.com")
    return store


# ============== Request/Response Fixtures ==============

@pytest.fixture
def sample_request() -> Request:
    """Sample GET request."""
    return Request(
        method="GET",
        url="https://example.com/api/test",
        headers={"Accept": "application/json"},
    )


@pytest.fixture
def post_request() -> Request:
    """Sample POST request with JSON body."""
    return Request(
        method="POST",
        url="https://example.com/api/data",
        headers={"Content-Type": "application/json"},
        json={"key": "value"},
    )


@pytest.fixture
def sample_response() -> Response:
    """Sample successful response."""
    return Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b'{"success": true}',
        url="https://example.com/api/test",
        cookies={"session": "abc123"},
        elapsed=0.5,
    )


@pytest.fixture
def error_response() -> Response:
    """Sample error response."""
    return Response(
        status_code=500,
        headers={"Content-Type": "text/plain"},
        content=b"Internal Server Error",
        url="https://example.com/api/test",
        elapsed=0.1,
    )


# ============== Mock Fixtures ==============

@pytest.fixture
def mock_transport() -> MagicMock:
    """Mock transport for testing without network."""
    transport = MagicMock(spec=CurlTransport)
    transport.is_closed = False

    # Default successful response
    transport.request_sync.return_value = Response(
        status_code=200,
        headers={"Content-Type": "text/html"},
        content=b"<html>OK</html>",
        url="https://example.com",
        elapsed=0.1,
    )

    # Async version
    async def async_request(*args, **kwargs):
        return transport.request_sync.return_value

    transport.request_async = AsyncMock(side_effect=async_request)

    return transport


@pytest.fixture
def mock_transport_with_cookies() -> MagicMock:
    """Mock transport that returns cookies."""
    transport = MagicMock(spec=CurlTransport)
    transport.is_closed = False

    transport.request_sync.return_value = Response(
        status_code=200,
        headers={"Content-Type": "text/html", "Set-Cookie": "session=abc123"},
        content=b"<html>OK</html>",
        url="https://example.com",
        cookies={"session": "abc123", "user": "testuser"},
        elapsed=0.1,
    )

    async def async_request(*args, **kwargs):
        return transport.request_sync.return_value

    transport.request_async = AsyncMock(side_effect=async_request)

    return transport


# ============== Client Fixtures ==============

@pytest.fixture
def client(mock_transport: MagicMock) -> Generator[ScraperClient, None, None]:
    """ScraperClient with mocked transport."""
    with patch("http_client.client.CurlTransport", return_value=mock_transport):
        client = ScraperClient(rate_limit=0)
        yield client
        client.close()


@pytest.fixture
def client_with_cookies(mock_transport_with_cookies: MagicMock) -> Generator[ScraperClient, None, None]:
    """ScraperClient with cookie persistence enabled."""
    with patch("http_client.client.CurlTransport", return_value=mock_transport_with_cookies):
        client = ScraperClient(persist_cookies=True, rate_limit=0)
        yield client
        client.close()


@pytest.fixture
async def async_client(mock_transport: MagicMock) -> AsyncGenerator[ScraperClient, None]:
    """Async ScraperClient with mocked transport."""
    with patch("http_client.client.CurlTransport", return_value=mock_transport):
        client = ScraperClient(rate_limit=0)
        yield client
        await client.close_async()


# ============== URL Fixtures ==============

@pytest.fixture
def test_urls() -> list[str]:
    """List of test URLs."""
    return [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
        "https://other.com/page1",
        "https://other.com/page2",
    ]


@pytest.fixture
def test_requests(test_urls: list[str]) -> list[Request]:
    """List of test requests."""
    return [Request(method="GET", url=url) for url in test_urls]


# ============== Event Loop Fixture ==============

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
