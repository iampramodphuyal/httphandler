"""Thread pool-based backend implementation."""

from __future__ import annotations

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Sequence

from ..config import ClientConfig
from ..fingerprint import HeaderGenerator, get_profile
from ..models import (
    AllProxiesFailed,
    BatchResult,
    MaxRetriesExceeded,
    Request,
    Response,
    TransportError,
)
from ..safety import CookieStore, DomainRateLimiter, ProxyPool
from ..transport import CurlTransport
from .base import BaseBackend


class ThreadBackend(BaseBackend):
    """Backend using ThreadPoolExecutor for concurrent request execution.

    Integrates transport, rate limiting, proxy management, and cookie
    storage for threaded execution model.
    """

    def __init__(
        self,
        config: ClientConfig,
        transport: CurlTransport | None = None,
        rate_limiter: DomainRateLimiter | None = None,
        proxy_pool: ProxyPool | None = None,
        cookie_store: CookieStore | None = None,
    ):
        """Initialize thread backend.

        Args:
            config: Client configuration.
            transport: HTTP transport (created if None).
            rate_limiter: Rate limiter (created if None and rate_limit > 0).
            proxy_pool: Proxy pool (created if None and proxies configured).
            cookie_store: Cookie store (created if None and persist_cookies=True).
        """
        super().__init__(config)

        # Get profile for fingerprinting
        self._profile = get_profile(config.profile)
        self._header_generator = HeaderGenerator(self._profile)

        # Transport
        impersonate = self._profile.impersonate if config.mode == "stealth" else None
        self._transport = transport or CurlTransport(
            impersonate=impersonate,
            default_timeout=config.timeout,
            connect_timeout=config.connect_timeout,
        )

        # Rate limiting
        self._rate_limiter: DomainRateLimiter | None = None
        if rate_limiter is not None:
            self._rate_limiter = rate_limiter
        elif config.rate_limit > 0:
            self._rate_limiter = DomainRateLimiter(default_rate=config.rate_limit)

        # Proxy pool
        self._proxy_pool: ProxyPool | None = None
        if proxy_pool is not None:
            self._proxy_pool = proxy_pool
        elif config.proxies:
            self._proxy_pool = ProxyPool(
                proxies=config.proxies,
                strategy=config.proxy_strategy,
                max_failures=config.proxy_max_failures,
                cooldown=config.proxy_cooldown,
            )

        # Cookie store
        self._cookie_store: CookieStore | None = None
        if cookie_store is not None:
            self._cookie_store = cookie_store
        elif config.persist_cookies:
            self._cookie_store = CookieStore()

        # Thread pool
        self._executor: ThreadPoolExecutor | None = None

    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create thread pool executor."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self._config.max_workers)
        return self._executor

    def _apply_stealth_delay(self) -> None:
        """Apply random delay in stealth mode."""
        if self._config.mode == "stealth":
            delay = random.uniform(self._config.min_delay, self._config.max_delay)
            time.sleep(delay)

    def _prepare_request(self, request: Request) -> Request:
        """Prepare request with headers, cookies, etc.

        Args:
            request: Original request.

        Returns:
            Prepared request with all headers and cookies set.
        """
        # Generate headers based on mode
        if self._config.mode == "stealth":
            headers = self._header_generator.generate(
                url=request.url,
                method=request.method,
                custom_headers=request.headers,
            )
        else:
            # Speed mode: minimal headers
            headers = dict(request.headers) if request.headers else {}
            if "User-Agent" not in headers:
                headers["User-Agent"] = "python-scraper/1.0"

        # Merge with config default headers
        final_headers = {**self._config.default_headers, **headers}

        # Create new request with prepared headers
        return Request(
            method=request.method,
            url=request.url,
            headers=final_headers,
            params=request.params,
            data=request.data,
            json=request.json,
            cookies=request.cookies,
            timeout=request.timeout,
            proxy=request.proxy,
        )

    def _get_cookies_for_request(self, url: str) -> dict[str, str]:
        """Get cookies from store for URL.

        Args:
            url: Request URL.

        Returns:
            Dict of cookies to send.
        """
        if self._cookie_store:
            return self._cookie_store.get_for_url(url)
        return {}

    def _store_response_cookies(self, url: str, cookies: dict[str, str]) -> None:
        """Store cookies from response.

        Args:
            url: Request URL.
            cookies: Response cookies.
        """
        if self._cookie_store and cookies:
            self._cookie_store.update_from_response(url, cookies)

    def _execute_with_retry(
        self,
        request: Request,
        proxy_url: str | None = None,
    ) -> Response:
        """Execute request with retry logic.

        Args:
            request: The request to execute.
            proxy_url: Optional proxy URL.

        Returns:
            Response object.

        Raises:
            MaxRetriesExceeded: If all retries exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(self._config.retries + 1):
            try:
                response = self._transport.request_sync(
                    request=request,
                    timeout=request.timeout or self._config.timeout,
                    proxy=proxy_url or request.proxy,
                    verify_ssl=self._config.verify_ssl,
                    follow_redirects=self._config.follow_redirects,
                    max_redirects=self._config.max_redirects,
                )

                # Check if we should retry based on status code
                if response.status_code in self._config.retry_codes:
                    if attempt < self._config.retries:
                        backoff = self._config.retry_backoff_base ** attempt
                        time.sleep(backoff)
                        continue

                return response

            except TransportError as e:
                last_error = e
                if attempt < self._config.retries:
                    backoff = self._config.retry_backoff_base ** attempt
                    time.sleep(backoff)
                    continue
                raise

        raise MaxRetriesExceeded(
            url=request.url,
            attempts=self._config.retries + 1,
            last_error=last_error,
        )

    def execute_sync(self, request: Request) -> Response:
        """Execute a single request synchronously.

        Args:
            request: The request to execute.

        Returns:
            Response object.
        """
        # Apply stealth delay before request
        self._apply_stealth_delay()

        # Rate limiting
        if self._rate_limiter:
            self._rate_limiter.acquire_sync(request.url)

        # Prepare request
        prepared = self._prepare_request(request)

        # Get cookies from store
        store_cookies = self._get_cookies_for_request(request.url)
        if store_cookies:
            merged_cookies = {**store_cookies, **(prepared.cookies or {})}
            prepared = Request(
                method=prepared.method,
                url=prepared.url,
                headers=prepared.headers,
                params=prepared.params,
                data=prepared.data,
                json=prepared.json,
                cookies=merged_cookies,
                timeout=prepared.timeout,
                proxy=prepared.proxy,
            )

        # Get proxy
        proxy_url: str | None = None
        proxy = None
        if self._proxy_pool:
            proxy = self._proxy_pool.get_proxy()
            if proxy:
                proxy_url = proxy.url

        try:
            response = self._execute_with_retry(prepared, proxy_url)

            # Report proxy success
            if proxy:
                self._proxy_pool.report_success(proxy.url)

            # Store response cookies
            self._store_response_cookies(request.url, response.cookies)

            return response

        except (TransportError, MaxRetriesExceeded) as e:
            # Report proxy failure
            if proxy:
                self._proxy_pool.report_failure(proxy.url)
            raise

    async def execute_async(self, request: Request) -> Response:
        """Execute a single request asynchronously (runs sync in thread pool).

        Args:
            request: The request to execute.

        Returns:
            Response object.
        """
        loop = asyncio.get_running_loop()
        executor = self._get_executor()
        return await loop.run_in_executor(executor, self.execute_sync, request)

    def gather_sync(
        self,
        requests: Sequence[Request],
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using thread pool.

        Args:
            requests: Sequence of requests to execute.
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        executor = self._get_executor()
        responses: list[Response | None] = [None] * len(requests)
        errors: dict[int, Exception] = {}
        stop_flag = False

        # Submit all tasks
        future_to_idx = {}
        for idx, req in enumerate(requests):
            if stop_flag:
                break
            future = executor.submit(self.execute_sync, req)
            future_to_idx[future] = idx

        # Collect results as they complete
        for future in as_completed(future_to_idx):
            if stop_flag and stop_on_error:
                # Cancel remaining futures
                future.cancel()
                continue

            idx = future_to_idx[future]
            try:
                responses[idx] = future.result()
            except Exception as e:
                errors[idx] = e
                if stop_on_error:
                    stop_flag = True

        return BatchResult(responses=responses, errors=errors)

    async def gather_async(
        self,
        requests: Sequence[Request],
        concurrency: int | None = None,
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using asyncio with thread pool.

        Args:
            requests: Sequence of requests to execute.
            concurrency: Max concurrent requests (uses thread pool size).
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        effective_concurrency = concurrency or self._config.default_concurrency
        semaphore = asyncio.Semaphore(effective_concurrency)
        stop_event = asyncio.Event() if stop_on_error else None

        responses: list[Response | None] = [None] * len(requests)
        errors: dict[int, Exception] = {}

        async def execute_one(idx: int, req: Request) -> None:
            if stop_event and stop_event.is_set():
                return

            async with semaphore:
                if stop_event and stop_event.is_set():
                    return

                try:
                    response = await self.execute_async(req)
                    responses[idx] = response
                except Exception as e:
                    errors[idx] = e
                    if stop_event:
                        stop_event.set()

        tasks = [execute_one(i, req) for i, req in enumerate(requests)]
        await asyncio.gather(*tasks, return_exceptions=True)

        return BatchResult(responses=responses, errors=errors)

    def close(self) -> None:
        """Close resources synchronously."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
        self._transport.close_sync()
        super().close()

    async def close_async(self) -> None:
        """Close async resources."""
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None
        await self._transport.close_async()
        await super().close_async()
