"""Asyncio-based backend implementation."""

from __future__ import annotations

import asyncio
import concurrent.futures
import random
import threading
import time
from typing import Any, Sequence

from ..config import ClientConfig
from ..fingerprint import HeaderGenerator, get_profile
from ..models import (
    AllProxiesFailed,
    BatchResult,
    MaxRetriesExceeded,
    RateLimitExceeded,
    Request,
    Response,
    TransportError,
)
from ..safety import CookieStore, DomainRateLimiter, ProxyPool
from ..transport import CurlTransport
from .base import BaseBackend


class AsyncBackend(BaseBackend):
    """Backend using asyncio for concurrent request execution.

    Integrates transport, rate limiting, proxy management, and cookie
    storage for async execution model.
    """

    # Shared executor for sync calls from async context (class-level)
    _sync_executor: "concurrent.futures.ThreadPoolExecutor | None" = None
    _executor_lock: "threading.Lock | None" = None

    def __init__(
        self,
        config: ClientConfig,
        transport: CurlTransport | None = None,
        rate_limiter: DomainRateLimiter | None = None,
        proxy_pool: ProxyPool | None = None,
        cookie_store: CookieStore | None = None,
    ):
        """Initialize async backend.

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

    async def _apply_stealth_delay(self) -> None:
        """Apply random delay in stealth mode."""
        if self._config.mode == "stealth":
            delay = random.uniform(self._config.min_delay, self._config.max_delay)
            await asyncio.sleep(delay)

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

    async def _get_cookies_for_request(self, url: str) -> dict[str, str]:
        """Get cookies from store for URL.

        Args:
            url: Request URL.

        Returns:
            Dict of cookies to send.
        """
        if self._cookie_store:
            return await self._cookie_store.get_for_url_async(url)
        return {}

    async def _store_response_cookies(self, url: str, cookies: dict[str, str]) -> None:
        """Store cookies from response.

        Args:
            url: Request URL.
            cookies: Response cookies.
        """
        if self._cookie_store and cookies:
            await self._cookie_store.update_from_response_async(url, cookies)

    async def _execute_with_retry(
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
                response = await self._transport.request_async(
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
                        await asyncio.sleep(backoff)
                        continue

                return response

            except TransportError as e:
                last_error = e
                if attempt < self._config.retries:
                    backoff = self._config.retry_backoff_base ** attempt
                    await asyncio.sleep(backoff)
                    continue
                raise

        raise MaxRetriesExceeded(
            url=request.url,
            attempts=self._config.retries + 1,
            last_error=last_error,
        )

    async def execute_async(self, request: Request) -> Response:
        """Execute a single request asynchronously.

        Args:
            request: The request to execute.

        Returns:
            Response object.

        Raises:
            RateLimitExceeded: If rate limit cannot be acquired (non-blocking mode).
        """
        # Apply stealth delay before request
        await self._apply_stealth_delay()

        # Rate limiting (blocking=True means it will wait for token)
        if self._rate_limiter:
            acquired = await self._rate_limiter.acquire_async(request.url, blocking=True)
            if not acquired:
                # This shouldn't happen with blocking=True, but handle it safely
                from urllib.parse import urlparse
                domain = urlparse(request.url).netloc
                raise RateLimitExceeded(domain=domain)

        # Prepare request
        prepared = self._prepare_request(request)

        # Get cookies from store and merge with request cookies
        store_cookies = await self._get_cookies_for_request(request.url)
        if store_cookies:
            merged_cookies = {**store_cookies, **(prepared.cookies or {})}
            prepared = prepared.with_cookies(merged_cookies)

        # Get proxy
        proxy_url: str | None = None
        proxy = None
        if self._proxy_pool:
            proxy = self._proxy_pool.get_proxy()
            if proxy:
                proxy_url = proxy.url

        try:
            response = await self._execute_with_retry(prepared, proxy_url)

            # Report proxy success
            if proxy:
                self._proxy_pool.report_success(proxy.url)

            # Store response cookies
            await self._store_response_cookies(request.url, response.cookies)

            return response

        except (TransportError, MaxRetriesExceeded) as e:
            # Report proxy failure
            if proxy:
                self._proxy_pool.report_failure(proxy.url)
            raise

    @classmethod
    def _get_sync_executor(cls) -> concurrent.futures.ThreadPoolExecutor:
        """Get or create the shared thread pool executor for sync calls.

        Uses double-checked locking to safely initialize the shared executor.

        Returns:
            Shared ThreadPoolExecutor instance.
        """
        if cls._sync_executor is None:
            if cls._executor_lock is None:
                cls._executor_lock = threading.Lock()
            with cls._executor_lock:
                if cls._sync_executor is None:
                    cls._sync_executor = concurrent.futures.ThreadPoolExecutor(
                        max_workers=4,
                        thread_name_prefix="async_backend_sync",
                    )
        return cls._sync_executor

    def _run_async_in_thread(self, request: Request) -> Response:
        """Run execute_async in a new event loop (for use in thread).

        This method is designed to be called from a thread pool worker.
        It creates the coroutine fresh in the worker thread's context.

        Args:
            request: The request to execute.

        Returns:
            Response object.
        """
        return asyncio.run(self.execute_async(request))

    def execute_sync(self, request: Request) -> Response:
        """Execute a single request synchronously (runs async in new loop).

        Args:
            request: The request to execute.

        Returns:
            Response object.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # We're in an async context - run in thread pool with new event loop.
            # Important: Don't create the coroutine here; let the worker thread
            # create it in its own event loop context.
            executor = self._get_sync_executor()
            future = executor.submit(self._run_async_in_thread, request)
            return future.result()
        else:
            # No running loop, safe to use asyncio.run directly
            return asyncio.run(self.execute_async(request))

    async def gather_async(
        self,
        requests: Sequence[Request],
        concurrency: int | None = None,
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using asyncio with semaphore.

        Args:
            requests: Sequence of requests to execute.
            concurrency: Max concurrent requests (None for config default).
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

    def _run_gather_in_thread(
        self,
        requests: Sequence[Request],
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Run gather_async in a new event loop (for use in thread).

        This method is designed to be called from a thread pool worker.
        It creates the coroutine fresh in the worker thread's context.

        Args:
            requests: Sequence of requests to execute.
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        return asyncio.run(
            self.gather_async(requests, stop_on_error=stop_on_error)
        )

    def gather_sync(
        self,
        requests: Sequence[Request],
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using thread pool (delegates to async).

        Args:
            requests: Sequence of requests to execute.
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # We're in an async context - run in thread pool with new event loop.
            executor = self._get_sync_executor()
            future = executor.submit(
                self._run_gather_in_thread, requests, stop_on_error
            )
            return future.result()
        else:
            # No running loop, safe to use asyncio.run directly
            return asyncio.run(
                self.gather_async(requests, stop_on_error=stop_on_error)
            )

    @classmethod
    def shutdown_executor(cls) -> None:
        """Shut down the shared thread pool executor.

        Call this when you're done with all AsyncBackend instances
        to clean up the shared executor resources.
        """
        if cls._sync_executor is not None:
            if cls._executor_lock is None:
                cls._executor_lock = threading.Lock()
            with cls._executor_lock:
                if cls._sync_executor is not None:
                    cls._sync_executor.shutdown(wait=True)
                    cls._sync_executor = None

    async def close_async(self) -> None:
        """Close async resources."""
        await self._transport.close_async()
        await super().close_async()

    def close(self) -> None:
        """Close resources synchronously."""
        self._transport.close_sync()
        super().close()
