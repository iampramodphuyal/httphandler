"""Main ScraperClient class providing unified HTTP client interface."""

from __future__ import annotations

from typing import Any, Sequence

from .backends import AsyncBackend, ThreadBackend
from .config import ClientConfig
from .fingerprint import get_profile
from .models import BatchResult, Request, Response
from .safety import CookieStore, DomainRateLimiter, ProxyPool
from .transport import CurlTransport


class ScraperClient:
    """Unified HTTP client for web scraping with dual execution model support.

    Supports both synchronous (thread pool) and asynchronous (asyncio) execution
    models with shared safety primitives (rate limiting, proxy pool, cookie store).

    Examples:
        # Simple sync usage
        client = ScraperClient()
        response = client.get("https://example.com")
        print(response.text)

        # Simple async usage
        async with ScraperClient() as client:
            response = await client.get_async("https://example.com")
            print(response.text)

        # Thread pool batch
        with ScraperClient(max_workers=20) as client:
            results = client.gather_sync(urls)

        # Async batch with concurrency
        async with ScraperClient() as client:
            results = await client.gather_async(urls, concurrency=50)

        # Stealth mode with cookies and proxies
        client = ScraperClient(
            mode="stealth",
            persist_cookies=True,
            profile="chrome_120",
            proxies=["socks5://proxy1:1080", "http://proxy2:8080"],
        )

        # Speed mode, no rate limiting
        client = ScraperClient(mode="speed", rate_limit=0)
    """

    def __init__(
        self,
        # Can pass a config object or individual kwargs
        config: ClientConfig | None = None,
        # Individual config options (override config if both provided)
        mode: str | None = None,
        persist_cookies: bool | None = None,
        profile: str | None = None,
        rate_limit: float | None = None,
        timeout: float | None = None,
        connect_timeout: float | None = None,
        retries: int | None = None,
        retry_codes: tuple[int, ...] | None = None,
        retry_backoff_base: float | None = None,
        proxies: list[str] | None = None,
        proxy_strategy: str | None = None,
        proxy_max_failures: int | None = None,
        proxy_cooldown: float | None = None,
        max_workers: int | None = None,
        default_concurrency: int | None = None,
        min_delay: float | None = None,
        max_delay: float | None = None,
        verify_ssl: bool | None = None,
        follow_redirects: bool | None = None,
        max_redirects: int | None = None,
        http_version: str | None = None,
        default_headers: dict[str, str] | None = None,
    ):
        """Initialize ScraperClient.

        Args:
            config: ClientConfig object (optional, can use kwargs instead).
            mode: Operating mode - "speed" or "stealth".
            persist_cookies: Whether to persist cookies between requests.
            profile: Browser profile for fingerprinting.
            rate_limit: Requests per second per domain (0 to disable).
            timeout: Total request timeout in seconds.
            connect_timeout: Connection timeout in seconds.
            retries: Number of retry attempts.
            retry_codes: HTTP status codes that trigger retry.
            retry_backoff_base: Base for exponential backoff.
            proxies: List of proxy URLs.
            proxy_strategy: Proxy rotation strategy.
            proxy_max_failures: Failures before disabling proxy.
            proxy_cooldown: Seconds before re-enabling failed proxy.
            max_workers: Thread pool size for gather_sync.
            default_concurrency: Semaphore limit for gather_async.
            min_delay: Minimum stealth mode delay.
            max_delay: Maximum stealth mode delay.
            verify_ssl: Whether to verify SSL certificates.
            follow_redirects: Whether to follow redirects.
            max_redirects: Maximum redirects to follow.
            http_version: HTTP version - "1.1", "2", or "auto".
            default_headers: Default headers for all requests.
        """
        # Validate profile name early (fail fast on invalid profile)
        profile_to_validate = profile if profile is not None else (
            config.profile if config is not None else "chrome_120"
        )
        try:
            get_profile(profile_to_validate)
        except ValueError as e:
            raise ValueError(f"Invalid profile configuration: {e}") from e

        # Build config from kwargs or use provided config
        if config is None:
            config_kwargs = {}
            if mode is not None:
                config_kwargs["mode"] = mode
            if persist_cookies is not None:
                config_kwargs["persist_cookies"] = persist_cookies
            if profile is not None:
                config_kwargs["profile"] = profile
            if rate_limit is not None:
                config_kwargs["rate_limit"] = rate_limit
            if timeout is not None:
                config_kwargs["timeout"] = timeout
            if connect_timeout is not None:
                config_kwargs["connect_timeout"] = connect_timeout
            if retries is not None:
                config_kwargs["retries"] = retries
            if retry_codes is not None:
                config_kwargs["retry_codes"] = retry_codes
            if retry_backoff_base is not None:
                config_kwargs["retry_backoff_base"] = retry_backoff_base
            if proxies is not None:
                config_kwargs["proxies"] = proxies
            if proxy_strategy is not None:
                config_kwargs["proxy_strategy"] = proxy_strategy
            if proxy_max_failures is not None:
                config_kwargs["proxy_max_failures"] = proxy_max_failures
            if proxy_cooldown is not None:
                config_kwargs["proxy_cooldown"] = proxy_cooldown
            if max_workers is not None:
                config_kwargs["max_workers"] = max_workers
            if default_concurrency is not None:
                config_kwargs["default_concurrency"] = default_concurrency
            if min_delay is not None:
                config_kwargs["min_delay"] = min_delay
            if max_delay is not None:
                config_kwargs["max_delay"] = max_delay
            if verify_ssl is not None:
                config_kwargs["verify_ssl"] = verify_ssl
            if follow_redirects is not None:
                config_kwargs["follow_redirects"] = follow_redirects
            if max_redirects is not None:
                config_kwargs["max_redirects"] = max_redirects
            if http_version is not None:
                config_kwargs["http_version"] = http_version
            if default_headers is not None:
                config_kwargs["default_headers"] = default_headers

            self._config = ClientConfig(**config_kwargs)
        else:
            self._config = config

        # Shared safety primitives
        self._rate_limiter: DomainRateLimiter | None = None
        if self._config.rate_limit > 0:
            self._rate_limiter = DomainRateLimiter(
                default_rate=self._config.rate_limit
            )

        self._proxy_pool: ProxyPool | None = None
        if self._config.proxies:
            self._proxy_pool = ProxyPool(
                proxies=self._config.proxies,
                strategy=self._config.proxy_strategy,
                max_failures=self._config.proxy_max_failures,
                cooldown=self._config.proxy_cooldown,
            )

        self._cookie_store: CookieStore | None = None
        if self._config.persist_cookies:
            self._cookie_store = CookieStore()

        # Create shared transport
        profile = get_profile(self._config.profile)
        impersonate = profile.impersonate if self._config.mode == "stealth" else None
        self._transport = CurlTransport(
            impersonate=impersonate,
            default_timeout=self._config.timeout,
            connect_timeout=self._config.connect_timeout,
            http_version=self._config.http_version,
        )

        # Create backends sharing the same primitives
        self._async_backend = AsyncBackend(
            config=self._config,
            transport=self._transport,
            rate_limiter=self._rate_limiter,
            proxy_pool=self._proxy_pool,
            cookie_store=self._cookie_store,
        )

        self._thread_backend = ThreadBackend(
            config=self._config,
            transport=self._transport,
            rate_limiter=self._rate_limiter,
            proxy_pool=self._proxy_pool,
            cookie_store=self._cookie_store,
        )

        self._closed = False

    @property
    def config(self) -> ClientConfig:
        """Get client configuration."""
        return self._config

    @property
    def cookie_store(self) -> CookieStore | None:
        """Get cookie store (None if persist_cookies=False)."""
        return self._cookie_store

    @property
    def proxy_pool(self) -> ProxyPool | None:
        """Get proxy pool (None if no proxies configured)."""
        return self._proxy_pool

    @property
    def rate_limiter(self) -> DomainRateLimiter | None:
        """Get rate limiter (None if rate_limit=0)."""
        return self._rate_limiter

    # ========== Sync Methods ==========

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make a synchronous HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data for POST requests.
            json: JSON body for POST requests.
            cookies: Cookies to send.
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.

        Returns:
            Response object.
        """
        request = Request(
            method=method,
            url=url,
            headers=headers or {},
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )
        return self._thread_backend.execute_sync(request)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make a synchronous GET request.

        Args:
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            cookies: Cookies to send.
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.

        Returns:
            Response object.
        """
        return self.request(
            "GET",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make a synchronous POST request.

        Args:
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data.
            json: JSON body.
            cookies: Cookies to send.
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.

        Returns:
            Response object.
        """
        return self.request(
            "POST",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    def put(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make a synchronous PUT request."""
        return self.request(
            "PUT",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    def delete(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make a synchronous DELETE request."""
        return self.request(
            "DELETE",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    def head(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make a synchronous HEAD request."""
        return self.request(
            "HEAD",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    def gather_sync(
        self,
        urls_or_requests: Sequence[str | Request],
        *,
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using thread pool.

        Args:
            urls_or_requests: List of URLs (for GET) or Request objects.
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        requests = [
            Request(method="GET", url=u) if isinstance(u, str) else u
            for u in urls_or_requests
        ]
        return self._thread_backend.gather_sync(requests, stop_on_error=stop_on_error)

    # ========== Async Methods ==========

    async def request_async(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make an asynchronous HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data for POST requests.
            json: JSON body for POST requests.
            cookies: Cookies to send.
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.

        Returns:
            Response object.
        """
        request = Request(
            method=method,
            url=url,
            headers=headers or {},
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )
        return await self._async_backend.execute_async(request)

    async def get_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make an asynchronous GET request.

        Args:
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            cookies: Cookies to send.
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.

        Returns:
            Response object.
        """
        return await self.request_async(
            "GET",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    async def post_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make an asynchronous POST request.

        Args:
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data.
            json: JSON body.
            cookies: Cookies to send.
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.

        Returns:
            Response object.
        """
        return await self.request_async(
            "POST",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    async def put_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make an asynchronous PUT request."""
        return await self.request_async(
            "PUT",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    async def delete_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make an asynchronous DELETE request."""
        return await self.request_async(
            "DELETE",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    async def head_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Make an asynchronous HEAD request."""
        return await self.request_async(
            "HEAD",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
        )

    async def gather_async(
        self,
        urls_or_requests: Sequence[str | Request],
        *,
        concurrency: int | None = None,
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using asyncio with semaphore.

        Args:
            urls_or_requests: List of URLs (for GET) or Request objects.
            concurrency: Max concurrent requests (None for config default).
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        requests = [
            Request(method="GET", url=u) if isinstance(u, str) else u
            for u in urls_or_requests
        ]
        return await self._async_backend.gather_async(
            requests,
            concurrency=concurrency,
            stop_on_error=stop_on_error,
        )

    # ========== Context Manager Support ==========

    def close(self) -> None:
        """Close client resources synchronously."""
        if not self._closed:
            self._thread_backend.close()
            self._async_backend.close()
            self._closed = True

    async def close_async(self) -> None:
        """Close client resources asynchronously."""
        if not self._closed:
            await self._async_backend.close_async()
            self._thread_backend.close()
            self._closed = True

    def __enter__(self) -> "ScraperClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> "ScraperClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close_async()

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        if not self._closed:
            try:
                self.close()
            except Exception:
                pass  # Ignore errors during cleanup
