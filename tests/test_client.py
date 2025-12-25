"""Integration tests for ScraperClient."""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from http_client import (
    ScraperClient,
    ClientConfig,
    Request,
    Response,
    TransportError,
    MaxRetriesExceeded,
)


class TestScraperClientInit:
    """Tests for ScraperClient initialization."""

    def test_init_defaults(self, mock_transport):
        """Test client initialization with defaults."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient()

            assert client.config.mode == "speed"
            assert client.config.persist_cookies is False
            assert client.cookie_store is None
            assert client.proxy_pool is None
            assert client.rate_limiter is not None  # Default rate limit is 2.0

            client.close()

    def test_init_with_config(self, mock_transport):
        """Test client initialization with ClientConfig."""
        config = ClientConfig(
            mode="stealth",
            persist_cookies=True,
            rate_limit=5.0,
        )

        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(config=config)

            assert client.config.mode == "stealth"
            assert client.config.persist_cookies is True
            assert client.cookie_store is not None

            client.close()

    def test_init_with_kwargs(self, mock_transport):
        """Test client initialization with kwargs."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(
                mode="stealth",
                persist_cookies=True,
                profile="firefox_121",
                rate_limit=0,
            )

            assert client.config.mode == "stealth"
            assert client.config.persist_cookies is True
            assert client.config.profile == "firefox_121"
            assert client.rate_limiter is None  # Disabled

            client.close()

    def test_init_with_proxies(self, mock_transport):
        """Test client initialization with proxies."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(
                proxies=["http://p1:8080", "http://p2:8080"],
                proxy_strategy="round_robin",
            )

            assert client.proxy_pool is not None
            assert client.proxy_pool.total_count == 2

            client.close()


class TestScraperClientSyncMethods:
    """Tests for synchronous client methods."""

    def test_get(self, client, mock_transport):
        """Test GET request."""
        response = client.get("https://example.com")

        assert response.status_code == 200
        assert mock_transport.request_sync.called or mock_transport.request_async.called

    def test_post(self, client, mock_transport):
        """Test POST request."""
        response = client.post(
            "https://example.com/api",
            json={"key": "value"},
        )

        assert response.status_code == 200

    def test_put(self, client, mock_transport):
        """Test PUT request."""
        response = client.put(
            "https://example.com/api/1",
            json={"key": "updated"},
        )

        assert response.status_code == 200

    def test_delete(self, client, mock_transport):
        """Test DELETE request."""
        response = client.delete("https://example.com/api/1")

        assert response.status_code == 200

    def test_head(self, client, mock_transport):
        """Test HEAD request."""
        response = client.head("https://example.com")

        assert response.status_code == 200

    def test_request_with_headers(self, client, mock_transport):
        """Test request with custom headers."""
        response = client.get(
            "https://example.com",
            headers={"X-Custom": "value"},
        )

        assert response.status_code == 200

    def test_request_with_params(self, client, mock_transport):
        """Test request with query parameters."""
        response = client.get(
            "https://example.com/search",
            params={"q": "test", "page": "1"},
        )

        assert response.status_code == 200

    def test_request_with_cookies(self, client, mock_transport):
        """Test request with cookies."""
        response = client.get(
            "https://example.com",
            cookies={"session": "abc123"},
        )

        assert response.status_code == 200

    def test_request_with_timeout(self, client, mock_transport):
        """Test request with custom timeout."""
        response = client.get(
            "https://example.com",
            timeout=5.0,
        )

        assert response.status_code == 200

    def test_request_with_proxy(self, client, mock_transport):
        """Test request with specific proxy."""
        response = client.get(
            "https://example.com",
            proxy="http://proxy:8080",
        )

        assert response.status_code == 200


class TestScraperClientAsyncMethods:
    """Tests for asynchronous client methods."""

    @pytest.mark.asyncio
    async def test_get_async(self, async_client, mock_transport):
        """Test async GET request."""
        response = await async_client.get_async("https://example.com")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_async(self, async_client, mock_transport):
        """Test async POST request."""
        response = await async_client.post_async(
            "https://example.com/api",
            json={"key": "value"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_put_async(self, async_client, mock_transport):
        """Test async PUT request."""
        response = await async_client.put_async(
            "https://example.com/api/1",
            data={"key": "updated"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_async(self, async_client, mock_transport):
        """Test async DELETE request."""
        response = await async_client.delete_async("https://example.com/api/1")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_head_async(self, async_client, mock_transport):
        """Test async HEAD request."""
        response = await async_client.head_async("https://example.com")

        assert response.status_code == 200


class TestScraperClientBatchOperations:
    """Tests for batch operations."""

    def test_gather_sync_with_urls(self, client, mock_transport):
        """Test gather_sync with URL list."""
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]

        results = client.gather_sync(urls)

        assert results.success_count == 3
        assert results.failure_count == 0
        assert results.all_succeeded

    def test_gather_sync_with_requests(self, client, mock_transport):
        """Test gather_sync with Request objects."""
        requests = [
            Request(method="GET", url="https://example.com/1"),
            Request(method="POST", url="https://example.com/2", json={"key": "value"}),
        ]

        results = client.gather_sync(requests)

        assert results.success_count == 2

    @pytest.mark.asyncio
    async def test_gather_async_with_urls(self, async_client, mock_transport):
        """Test gather_async with URL list."""
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]

        results = await async_client.gather_async(urls)

        assert results.success_count == 3
        assert results.all_succeeded

    @pytest.mark.asyncio
    async def test_gather_async_with_concurrency(self, async_client, mock_transport):
        """Test gather_async with custom concurrency."""
        urls = ["https://example.com/" + str(i) for i in range(10)]

        results = await async_client.gather_async(urls, concurrency=3)

        assert results.success_count == 10


class TestScraperClientCookies:
    """Tests for cookie handling."""

    def test_cookies_not_persisted_by_default(self, mock_transport_with_cookies):
        """Test cookies are not persisted by default."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport_with_cookies):
            client = ScraperClient(rate_limit=0)

            # First request sets cookies
            client.get("https://example.com/login")

            # Cookie store should be None
            assert client.cookie_store is None

            client.close()

    def test_cookies_persisted_when_enabled(self, mock_transport_with_cookies):
        """Test cookies are persisted when enabled."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport_with_cookies):
            client = ScraperClient(persist_cookies=True, rate_limit=0)

            # Cookie store should exist
            assert client.cookie_store is not None

            # First request sets cookies
            response = client.get("https://example.com/login")

            # Response should have cookies
            assert len(response.cookies) > 0

            # Manually verify cookie store is accessible
            # (The actual storage depends on the backend implementation)
            assert client.cookie_store is not None

            client.close()


class TestScraperClientContextManager:
    """Tests for context manager support."""

    def test_sync_context_manager(self, mock_transport):
        """Test sync context manager."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            with ScraperClient(rate_limit=0) as client:
                response = client.get("https://example.com")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_transport):
        """Test async context manager."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            async with ScraperClient(rate_limit=0) as client:
                response = await client.get_async("https://example.com")
                assert response.status_code == 200


class TestScraperClientModes:
    """Tests for speed vs stealth modes."""

    def test_speed_mode_no_delay(self, mock_transport):
        """Test speed mode has no artificial delays."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(mode="speed", rate_limit=0)

            # Should complete quickly without delays
            import time
            start = time.monotonic()
            for _ in range(5):
                client.get("https://example.com")
            elapsed = time.monotonic() - start

            # Should be very fast without delays
            assert elapsed < 1.0

            client.close()

    def test_stealth_mode_config(self, mock_transport):
        """Test stealth mode configuration."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(
                mode="stealth",
                profile="chrome_120",
                min_delay=0.01,
                max_delay=0.02,
                rate_limit=0,
            )

            assert client.config.mode == "stealth"
            assert client.config.profile == "chrome_120"

            client.close()


class TestScraperClientRateLimiting:
    """Tests for rate limiting integration."""

    def test_rate_limiter_created(self, mock_transport):
        """Test rate limiter is created when rate_limit > 0."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(rate_limit=5.0)

            assert client.rate_limiter is not None

            client.close()

    def test_rate_limiter_disabled(self, mock_transport):
        """Test rate limiter is not created when rate_limit = 0."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(rate_limit=0)

            assert client.rate_limiter is None

            client.close()


class TestScraperClientProxyIntegration:
    """Tests for proxy pool integration."""

    def test_proxy_pool_created(self, mock_transport):
        """Test proxy pool is created when proxies configured."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(
                proxies=["http://p1:8080", "http://p2:8080"],
                rate_limit=0,
            )

            assert client.proxy_pool is not None
            assert client.proxy_pool.total_count == 2

            client.close()

    def test_proxy_pool_not_created(self, mock_transport):
        """Test proxy pool is not created when no proxies."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(rate_limit=0)

            assert client.proxy_pool is None

            client.close()


class TestScraperClientErrorHandling:
    """Tests for error handling."""

    def test_transport_error_handling(self, mock_transport):
        """Test transport error is propagated."""
        mock_transport.request_sync.side_effect = TransportError("Connection failed")

        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(rate_limit=0, retries=0)

            with pytest.raises(TransportError):
                client.get("https://example.com")

            client.close()

    def test_batch_error_isolation(self, mock_transport):
        """Test errors are isolated in batch operations."""
        call_count = [0]

        def mock_request(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise TransportError("Connection failed")
            return Response(
                status_code=200,
                headers={},
                content=b"OK",
                url="https://example.com",
            )

        mock_transport.request_sync.side_effect = mock_request

        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(rate_limit=0, retries=0)

            urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
            results = client.gather_sync(urls)

            # Should have 2 successes and 1 failure
            assert results.success_count == 2
            assert results.failure_count == 1
            assert len(results.errors) == 1  # One error occurred

            client.close()


class TestScraperClientConfiguration:
    """Tests for configuration properties."""

    def test_config_property(self, mock_transport):
        """Test config property returns configuration."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(
                mode="stealth",
                timeout=60.0,
                rate_limit=0,
            )

            assert client.config.mode == "stealth"
            assert client.config.timeout == 60.0

            client.close()

    def test_all_config_options(self, mock_transport):
        """Test all configuration options are applied."""
        with patch("http_client.client.CurlTransport", return_value=mock_transport):
            client = ScraperClient(
                mode="stealth",
                persist_cookies=True,
                profile="firefox_121",
                rate_limit=5.0,
                timeout=45.0,
                connect_timeout=15.0,
                retries=5,
                retry_codes=(500, 502, 503),
                retry_backoff_base=3.0,
                proxies=["http://proxy:8080"],
                proxy_strategy="random",
                proxy_max_failures=5,
                proxy_cooldown=600.0,
                max_workers=20,
                default_concurrency=20,
                min_delay=2.0,
                max_delay=5.0,
                verify_ssl=False,
                follow_redirects=False,
                max_redirects=5,
                default_headers={"X-Custom": "value"},
            )

            config = client.config
            assert config.mode == "stealth"
            assert config.persist_cookies is True
            assert config.profile == "firefox_121"
            assert config.rate_limit == 5.0
            assert config.timeout == 45.0
            assert config.connect_timeout == 15.0
            assert config.retries == 5
            assert config.retry_codes == (500, 502, 503)
            assert config.retry_backoff_base == 3.0
            assert config.proxies == ["http://proxy:8080"]
            assert config.proxy_strategy == "random"
            assert config.proxy_max_failures == 5
            assert config.proxy_cooldown == 600.0
            assert config.max_workers == 20
            assert config.default_concurrency == 20
            assert config.min_delay == 2.0
            assert config.max_delay == 5.0
            assert config.verify_ssl is False
            assert config.follow_redirects is False
            assert config.max_redirects == 5
            assert config.default_headers == {"X-Custom": "value"}

            client.close()
