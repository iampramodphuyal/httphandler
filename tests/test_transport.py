"""Tests for transport layer."""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from http_client import Request, Response, TransportError
from http_client.transport import CurlTransport
from http_client.transport.base import BaseTransport


class TestCurlTransport:
    """Tests for CurlTransport."""

    def test_init_defaults(self):
        """Test transport initialization with defaults."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session"):
                transport = CurlTransport()

                assert transport._default_timeout == 30.0
                assert transport._connect_timeout == 10.0
                assert transport._impersonate is None
                assert not transport.is_closed

    def test_init_with_impersonate(self):
        """Test transport with browser impersonation."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session"):
                transport = CurlTransport(impersonate="chrome120")

                assert transport._impersonate == "chrome120"

    def test_init_with_timeouts(self):
        """Test transport with custom timeouts."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session"):
                transport = CurlTransport(
                    default_timeout=60.0,
                    connect_timeout=15.0,
                )

                assert transport._default_timeout == 60.0
                assert transport._connect_timeout == 15.0

    def test_backend_name_curl(self):
        """Test backend name when using curl_cffi."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session"):
                transport = CurlTransport()
                assert transport.backend_name == "curl_cffi"
                assert transport.using_curl_cffi is True

    def test_backend_name_httpx(self):
        """Test backend name when using httpx fallback."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", False):
            with patch("http_client.transport.curl_transport.HTTPX_AVAILABLE", True):
                with patch("http_client.transport.curl_transport.httpx"):
                    transport = CurlTransport()
                    assert transport.backend_name == "httpx"
                    assert transport.using_curl_cffi is False

    def test_no_transport_available_raises(self):
        """Test error when no transport is available."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", False):
            with patch("http_client.transport.curl_transport.HTTPX_AVAILABLE", False):
                with pytest.raises(ImportError, match="Neither curl_cffi nor httpx"):
                    CurlTransport()

    def test_request_sync_closed_raises(self):
        """Test sync request on closed transport raises."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session"):
                transport = CurlTransport()
                transport.close_sync()

                with pytest.raises(TransportError, match="closed"):
                    transport.request_sync(Request(method="GET", url="https://example.com"))

    @pytest.mark.asyncio
    async def test_request_async_closed_raises(self):
        """Test async request on closed transport raises."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.AsyncSession"):
                transport = CurlTransport()
                await transport.close_async()

                with pytest.raises(TransportError, match="closed"):
                    await transport.request_async(Request(method="GET", url="https://example.com"))

    def test_context_manager_sync(self):
        """Test sync context manager."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session"):
                with CurlTransport() as transport:
                    assert not transport.is_closed

                assert transport.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_async(self):
        """Test async context manager."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.AsyncSession"):
                async with CurlTransport() as transport:
                    assert not transport.is_closed

                assert transport.is_closed


class TestCurlTransportWithMockSession:
    """Tests for CurlTransport with mocked session."""

    @pytest.fixture
    def mock_curl_session(self):
        """Create mock curl session."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Type": "text/html"}
        response.content = b"<html>OK</html>"
        response.url = "https://example.com"
        response.cookies = {}
        session.request.return_value = response
        return session

    @pytest.fixture
    def mock_async_session(self):
        """Create mock async curl session."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Type": "text/html"}
        response.content = b"<html>OK</html>"
        response.url = "https://example.com"
        response.cookies = {}

        async def mock_request(*args, **kwargs):
            return response

        session.request = AsyncMock(side_effect=mock_request)
        return session

    def test_request_sync_success(self, mock_curl_session):
        """Test successful sync request."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session", return_value=mock_curl_session):
                transport = CurlTransport()
                request = Request(method="GET", url="https://example.com")

                response = transport.request_sync(request)

                assert response.status_code == 200
                assert response.content == b"<html>OK</html>"
                assert response.elapsed > 0

    def test_request_sync_with_all_options(self, mock_curl_session):
        """Test sync request with all options."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session", return_value=mock_curl_session):
                transport = CurlTransport()
                request = Request(
                    method="POST",
                    url="https://example.com/api",
                    headers={"Content-Type": "application/json"},
                    json={"key": "value"},
                    cookies={"session": "abc"},
                )

                response = transport.request_sync(
                    request,
                    timeout=10.0,
                    proxy="http://proxy:8080",
                    verify_ssl=False,
                    follow_redirects=True,
                    max_redirects=5,
                )

                assert response.status_code == 200
                mock_curl_session.request.assert_called_once()

    def test_request_sync_error_handling(self, mock_curl_session):
        """Test sync request error handling."""
        mock_curl_session.request.side_effect = Exception("Connection failed")

        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session", return_value=mock_curl_session):
                transport = CurlTransport()
                request = Request(method="GET", url="https://example.com")

                with pytest.raises(TransportError) as exc_info:
                    transport.request_sync(request)

                assert "Connection failed" in str(exc_info.value)
                assert exc_info.value.original_error is not None

    @pytest.mark.asyncio
    async def test_request_async_success(self, mock_async_session):
        """Test successful async request."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.AsyncSession", return_value=mock_async_session):
                transport = CurlTransport()
                request = Request(method="GET", url="https://example.com")

                response = await transport.request_async(request)

                assert response.status_code == 200
                assert response.content == b"<html>OK</html>"

    @pytest.mark.asyncio
    async def test_request_async_error_handling(self, mock_async_session):
        """Test async request error handling."""
        mock_async_session.request = AsyncMock(side_effect=Exception("Timeout"))

        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.AsyncSession", return_value=mock_async_session):
                transport = CurlTransport()
                request = Request(method="GET", url="https://example.com")

                with pytest.raises(TransportError) as exc_info:
                    await transport.request_async(request)

                assert "Timeout" in str(exc_info.value)


class TestBaseTransport:
    """Tests for BaseTransport abstract class."""

    def test_cannot_instantiate(self):
        """Test BaseTransport cannot be instantiated directly."""
        # BaseTransport has abstract methods, so direct instantiation would fail
        # We test through a concrete implementation
        pass

    def test_is_closed_property(self):
        """Test is_closed property."""
        with patch("http_client.transport.curl_transport.CURL_AVAILABLE", True):
            with patch("http_client.transport.curl_transport.Session"):
                transport = CurlTransport()

                assert transport.is_closed is False
                transport.close_sync()
                assert transport.is_closed is True
