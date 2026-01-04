"""Shared test fixtures and configuration."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from http_client import HTTPClient, Request, Response
from http_client._cookies import CookieStore


# ============== Cookie Store Fixtures ==============

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


# ============== Mock Backend Fixtures ==============

@pytest.fixture
def mock_httpx_backend() -> MagicMock:
    """Mock httpx backend for testing without network."""
    backend = MagicMock()

    # Default successful response
    backend.request_sync.return_value = Response(
        status_code=200,
        headers={"Content-Type": "text/html"},
        content=b"<html>OK</html>",
        url="https://example.com",
        elapsed=0.1,
    )

    # Async version
    async def async_request(*args, **kwargs):
        return backend.request_sync.return_value

    backend.request_async = AsyncMock(side_effect=async_request)
    backend.close_sync = MagicMock()
    backend.close_async = AsyncMock()

    return backend


@pytest.fixture
def mock_curl_backend() -> MagicMock:
    """Mock curl backend for testing without network."""
    backend = MagicMock()

    # Default successful response
    backend.request_sync.return_value = Response(
        status_code=200,
        headers={"Content-Type": "text/html"},
        content=b"<html>OK</html>",
        url="https://example.com",
        elapsed=0.1,
    )

    # Async version
    async def async_request(*args, **kwargs):
        return backend.request_sync.return_value

    backend.request_async = AsyncMock(side_effect=async_request)
    backend.close_sync = MagicMock()
    backend.close_async = AsyncMock()

    return backend


@pytest.fixture
def mock_backend_with_cookies() -> MagicMock:
    """Mock backend that returns cookies."""
    backend = MagicMock()

    backend.request_sync.return_value = Response(
        status_code=200,
        headers={"Content-Type": "text/html", "Set-Cookie": "session=abc123"},
        content=b"<html>OK</html>",
        url="https://example.com",
        cookies={"session": "abc123", "user": "testuser"},
        elapsed=0.1,
    )

    async def async_request(*args, **kwargs):
        return backend.request_sync.return_value

    backend.request_async = AsyncMock(side_effect=async_request)
    backend.close_sync = MagicMock()
    backend.close_async = AsyncMock()

    return backend


# ============== Client Fixtures ==============

@pytest.fixture
def client(mock_httpx_backend: MagicMock) -> Generator[HTTPClient, None, None]:
    """HTTPClient with mocked httpx backend."""
    with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
        client = HTTPClient()
        yield client
        client.close()


@pytest.fixture
def client_with_cookies(mock_backend_with_cookies: MagicMock) -> Generator[HTTPClient, None, None]:
    """HTTPClient with cookie persistence enabled."""
    with patch("http_client.client.HttpxBackend", return_value=mock_backend_with_cookies):
        client = HTTPClient(persist_cookies=True)
        yield client
        client.close()


@pytest.fixture
async def async_client(mock_httpx_backend: MagicMock) -> AsyncGenerator[HTTPClient, None]:
    """Async HTTPClient with mocked backend."""
    with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
        client = HTTPClient()
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


# ============== Event Loop Fixture ==============

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
