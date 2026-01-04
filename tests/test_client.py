"""Tests for HTTPClient."""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from http_client import (
    HTTPClient,
    Response,
    TransportError,
)


class TestHTTPClientInit:
    """Tests for HTTPClient initialization."""

    def test_init_defaults(self, mock_httpx_backend):
        """Test client initialization with defaults."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            client = HTTPClient()

            assert client._default_backend == "httpx"
            assert client._cookie_store is None
            assert client._timeout == 30.0
            assert client._verify_ssl is True
            assert client._proxy is None
            assert client._follow_redirects is True
            assert client._profile == "chrome_120"

            client.close()

    def test_init_with_cookie_persistence(self, mock_httpx_backend):
        """Test client initialization with cookie persistence."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            client = HTTPClient(persist_cookies=True)

            assert client._cookie_store is not None

            client.close()

    def test_init_with_curl_backend(self, mock_curl_backend):
        """Test client initialization with curl backend."""
        with patch("http_client.client.CurlBackend", return_value=mock_curl_backend):
            with patch("http_client.client.CURL_AVAILABLE", True):
                client = HTTPClient(default_backend="curl")

                assert client._default_backend == "curl"

                client.close()

    def test_init_with_custom_options(self, mock_httpx_backend):
        """Test client initialization with custom options."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            client = HTTPClient(
                timeout=60.0,
                headers={"X-Custom": "value"},
                verify_ssl=False,
                proxy="http://proxy:8080",
                follow_redirects=False,
                profile="firefox_121",
            )

            assert client._timeout == 60.0
            assert client._default_headers == {"X-Custom": "value"}
            assert client._verify_ssl is False
            assert client._proxy == "http://proxy:8080"
            assert client._follow_redirects is False
            assert client._profile == "firefox_121"

            client.close()


class TestHTTPClientSyncMethods:
    """Tests for synchronous client methods."""

    def test_get(self, client, mock_httpx_backend):
        """Test GET request."""
        response = client.get("https://example.com")

        assert response.status_code == 200

    def test_post(self, client, mock_httpx_backend):
        """Test POST request."""
        response = client.post(
            "https://example.com/api",
            json={"key": "value"},
        )

        assert response.status_code == 200

    def test_put(self, client, mock_httpx_backend):
        """Test PUT request."""
        response = client.put(
            "https://example.com/api/1",
            json={"key": "updated"},
        )

        assert response.status_code == 200

    def test_delete(self, client, mock_httpx_backend):
        """Test DELETE request."""
        response = client.delete("https://example.com/api/1")

        assert response.status_code == 200

    def test_patch(self, client, mock_httpx_backend):
        """Test PATCH request."""
        response = client.patch(
            "https://example.com/api/1",
            json={"key": "patched"},
        )

        assert response.status_code == 200

    def test_head(self, client, mock_httpx_backend):
        """Test HEAD request."""
        response = client.head("https://example.com")

        assert response.status_code == 200

    def test_options(self, client, mock_httpx_backend):
        """Test OPTIONS request."""
        response = client.options("https://example.com")

        assert response.status_code == 200

    def test_request_with_headers(self, client, mock_httpx_backend):
        """Test request with custom headers."""
        response = client.get(
            "https://example.com",
            headers={"X-Custom": "value"},
        )

        assert response.status_code == 200

    def test_request_with_params(self, client, mock_httpx_backend):
        """Test request with query parameters."""
        response = client.get(
            "https://example.com/search",
            params={"q": "test", "page": "1"},
        )

        assert response.status_code == 200

    def test_request_with_cookies(self, client, mock_httpx_backend):
        """Test request with cookies."""
        response = client.get(
            "https://example.com",
            cookies={"session": "abc123"},
        )

        assert response.status_code == 200

    def test_request_with_timeout(self, client, mock_httpx_backend):
        """Test request with custom timeout."""
        response = client.get(
            "https://example.com",
            timeout=5.0,
        )

        assert response.status_code == 200

    def test_request_with_proxy(self, client, mock_httpx_backend):
        """Test request with specific proxy."""
        response = client.get(
            "https://example.com",
            proxy="http://proxy:8080",
        )

        assert response.status_code == 200


class TestHTTPClientAsyncMethods:
    """Tests for asynchronous client methods."""

    @pytest.mark.asyncio
    async def test_get_async(self, async_client, mock_httpx_backend):
        """Test async GET request."""
        response = await async_client.get_async("https://example.com")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_async(self, async_client, mock_httpx_backend):
        """Test async POST request."""
        response = await async_client.post_async(
            "https://example.com/api",
            json={"key": "value"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_put_async(self, async_client, mock_httpx_backend):
        """Test async PUT request."""
        response = await async_client.put_async(
            "https://example.com/api/1",
            data={"key": "updated"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_async(self, async_client, mock_httpx_backend):
        """Test async DELETE request."""
        response = await async_client.delete_async("https://example.com/api/1")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_patch_async(self, async_client, mock_httpx_backend):
        """Test async PATCH request."""
        response = await async_client.patch_async(
            "https://example.com/api/1",
            json={"key": "patched"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_head_async(self, async_client, mock_httpx_backend):
        """Test async HEAD request."""
        response = await async_client.head_async("https://example.com")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_options_async(self, async_client, mock_httpx_backend):
        """Test async OPTIONS request."""
        response = await async_client.options_async("https://example.com")

        assert response.status_code == 200


class TestHTTPClientCookies:
    """Tests for cookie handling."""

    def test_cookies_not_persisted_by_default(self, mock_backend_with_cookies):
        """Test cookies are not persisted by default."""
        with patch("http_client.client.HttpxBackend", return_value=mock_backend_with_cookies):
            client = HTTPClient()

            # Cookie store should be None
            assert client._cookie_store is None

            # First request returns cookies
            response = client.get("https://example.com/login")
            assert len(response.cookies) > 0

            client.close()

    def test_cookies_persisted_when_enabled(self, mock_backend_with_cookies):
        """Test cookies are persisted when enabled."""
        with patch("http_client.client.HttpxBackend", return_value=mock_backend_with_cookies):
            client = HTTPClient(persist_cookies=True)

            # Cookie store should exist
            assert client._cookie_store is not None

            # First request sets cookies
            response = client.get("https://example.com/login")

            # Response should have cookies
            assert len(response.cookies) > 0

            # Cookies should be stored (verify via cookie store directly)
            stored_cookies = client._cookie_store.get_for_url("https://example.com")
            assert len(stored_cookies) > 0
            assert "session" in stored_cookies

            client.close()

    def test_clear_cookies(self, mock_backend_with_cookies):
        """Test clearing cookies."""
        with patch("http_client.client.HttpxBackend", return_value=mock_backend_with_cookies):
            client = HTTPClient(persist_cookies=True)

            # Set some cookies
            client.get("https://example.com")

            # Clear all cookies
            client.clear_cookies()

            assert client.cookies == {}

            client.close()

    def test_clear_cookies_by_domain(self, mock_backend_with_cookies):
        """Test clearing cookies for specific domain."""
        with patch("http_client.client.HttpxBackend", return_value=mock_backend_with_cookies):
            client = HTTPClient(persist_cookies=True)

            # Set some cookies
            client.get("https://example.com")

            # Clear cookies for domain
            client.clear_cookies("example.com")

            assert client.cookies.get("example.com", {}) == {}

            client.close()


class TestHTTPClientHelpers:
    """Tests for helper methods."""

    def test_get_status_code(self, client, mock_httpx_backend):
        """Test get_status_code helper."""
        assert client.get_status_code() is None

        client.get("https://example.com")

        assert client.get_status_code() == 200

    def test_get_headers(self, client, mock_httpx_backend):
        """Test get_headers helper."""
        assert client.get_headers() is None

        client.get("https://example.com")

        headers = client.get_headers()
        assert headers is not None
        assert "Content-Type" in headers

    def test_get_cookies(self, client, mock_httpx_backend):
        """Test get_cookies helper."""
        assert client.get_cookies() is None

        client.get("https://example.com")

        # Response may or may not have cookies depending on mock
        cookies = client.get_cookies()
        assert cookies is not None

    def test_get_current_proxy(self, mock_httpx_backend):
        """Test get_current_proxy helper."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            client = HTTPClient(proxy="http://proxy:8080")

            assert client.get_current_proxy() == "http://proxy:8080"

            client.close()

    def test_get_elapsed(self, client, mock_httpx_backend):
        """Test get_elapsed helper."""
        assert client.get_elapsed() is None

        client.get("https://example.com")

        elapsed = client.get_elapsed()
        assert elapsed is not None
        assert elapsed >= 0

    def test_last_response_property(self, client, mock_httpx_backend):
        """Test last_response property."""
        assert client.last_response is None

        client.get("https://example.com")

        assert client.last_response is not None
        assert isinstance(client.last_response, Response)


class TestHTTPClientHeaderManagement:
    """Tests for header management."""

    def test_set_default_header(self, client, mock_httpx_backend):
        """Test setting default header."""
        client.set_default_header("X-Custom", "value")

        assert client._default_headers["X-Custom"] == "value"

    def test_remove_default_header(self, client, mock_httpx_backend):
        """Test removing default header."""
        client.set_default_header("X-Custom", "value")
        client.remove_default_header("X-Custom")

        assert "X-Custom" not in client._default_headers

    def test_remove_nonexistent_header(self, client, mock_httpx_backend):
        """Test removing nonexistent header doesn't raise."""
        client.remove_default_header("X-NonExistent")  # Should not raise


class TestHTTPClientProxyManagement:
    """Tests for proxy management."""

    def test_set_proxy(self, client, mock_httpx_backend):
        """Test setting proxy."""
        client.set_proxy("http://newproxy:8080")

        assert client._proxy == "http://newproxy:8080"

    def test_clear_proxy(self, client, mock_httpx_backend):
        """Test clearing proxy."""
        client.set_proxy("http://proxy:8080")
        client.set_proxy(None)

        assert client._proxy is None


class TestHTTPClientContextManager:
    """Tests for context manager support."""

    def test_sync_context_manager(self, mock_httpx_backend):
        """Test sync context manager."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            with HTTPClient() as client:
                response = client.get("https://example.com")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_httpx_backend):
        """Test async context manager."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            async with HTTPClient() as client:
                response = await client.get_async("https://example.com")
                assert response.status_code == 200


class TestHTTPClientBackendSwitching:
    """Tests for per-request backend switching."""

    def test_default_backend_httpx(self, mock_httpx_backend):
        """Test default backend is httpx."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            client = HTTPClient()

            # Should use httpx by default
            client.get("https://example.com")

            assert mock_httpx_backend.request_sync.called

            client.close()

    def test_switch_to_curl_backend(self, mock_httpx_backend, mock_curl_backend):
        """Test switching to curl backend per request."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            with patch("http_client.client.CurlBackend", return_value=mock_curl_backend):
                with patch("http_client.client.CURL_AVAILABLE", True):
                    client = HTTPClient()

                    # Switch to curl for this request
                    client.get("https://example.com", backend="curl")

                    assert mock_curl_backend.request_sync.called

                    client.close()

    def test_stealth_mode_curl(self, mock_httpx_backend, mock_curl_backend):
        """Test stealth mode with curl backend."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            with patch("http_client.client.CurlBackend", return_value=mock_curl_backend):
                with patch("http_client.client.CURL_AVAILABLE", True):
                    client = HTTPClient()

                    # Use stealth mode
                    client.get("https://example.com", backend="curl", stealth=True)

                    # Verify curl backend was called with stealth=True
                    call_kwargs = mock_curl_backend.request_sync.call_args[1]
                    assert call_kwargs.get("stealth") is True

                    client.close()


class TestHTTPClientErrorHandling:
    """Tests for error handling."""

    def test_closed_client_raises_error(self, mock_httpx_backend):
        """Test that using closed client raises RuntimeError."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            client = HTTPClient()
            client.close()

            with pytest.raises(RuntimeError, match="Client is closed"):
                client.get("https://example.com")

    def test_transport_error_propagates(self, mock_httpx_backend):
        """Test transport error is propagated."""
        mock_httpx_backend.request_sync.side_effect = TransportError("Connection failed")

        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            client = HTTPClient()

            with pytest.raises(TransportError):
                client.get("https://example.com")

            client.close()

    def test_curl_not_available_raises(self, mock_httpx_backend):
        """Test error when curl is not available."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend):
            with patch("http_client.client.CURL_AVAILABLE", False):
                client = HTTPClient()

                with pytest.raises(ImportError, match="curl_cffi is required"):
                    client.get("https://example.com", backend="curl")

                client.close()


class TestHTTPClientLazyBackendInit:
    """Tests for lazy backend initialization."""

    def test_httpx_backend_lazy_init(self, mock_httpx_backend):
        """Test httpx backend is lazily initialized."""
        with patch("http_client.client.HttpxBackend", return_value=mock_httpx_backend) as mock_class:
            client = HTTPClient()

            # Backend not created yet
            assert client._httpx_backend is None

            # Make request
            client.get("https://example.com")

            # Now backend should be created
            assert client._httpx_backend is not None

            client.close()

    def test_curl_backend_lazy_init(self, mock_curl_backend):
        """Test curl backend is lazily initialized."""
        with patch("http_client.client.CurlBackend", return_value=mock_curl_backend) as mock_class:
            with patch("http_client.client.CURL_AVAILABLE", True):
                client = HTTPClient(default_backend="curl")

                # Backend not created yet
                assert client._curl_backend is None

                # Make request
                client.get("https://example.com")

                # Now backend should be created
                assert client._curl_backend is not None

                client.close()
