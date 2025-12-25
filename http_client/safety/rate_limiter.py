"""Thread-safe and async-safe rate limiting with token bucket algorithm."""

from __future__ import annotations

import asyncio
import threading
import time
from urllib.parse import urlparse


class TokenBucket:
    """Token bucket rate limiter with dual-lock pattern for thread and async safety.

    The token bucket algorithm allows for bursty traffic while maintaining
    an average rate limit. Tokens are added at a constant rate and consumed
    by each request.
    """

    def __init__(self, rate: float, capacity: float | None = None):
        """Initialize token bucket.

        Args:
            rate: Tokens added per second (requests/second limit).
            capacity: Maximum token capacity for bursts. Defaults to rate.
        """
        self._rate = rate
        self._capacity = capacity if capacity is not None else rate
        self._tokens = self._capacity
        self._last_update = time.monotonic()

        # Dual-lock pattern
        self._thread_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazily initialize async lock within event loop context."""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def _refill(self) -> None:
        """Refill tokens based on elapsed time. Must be called under lock."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_update = now

    def _calculate_wait_time(self) -> float:
        """Calculate time to wait for one token. Must be called under lock."""
        if self._tokens >= 1:
            return 0.0
        return (1 - self._tokens) / self._rate

    def acquire_sync(self, blocking: bool = True) -> bool:
        """Acquire a token synchronously (blocking).

        Args:
            blocking: If True, wait for token. If False, return immediately.

        Returns:
            True if token acquired, False if non-blocking and no token available.
        """
        with self._thread_lock:
            self._refill()

            if self._tokens >= 1:
                self._tokens -= 1
                return True

            if not blocking:
                return False

            wait_time = self._calculate_wait_time()

        # Sleep outside lock to allow other threads to proceed
        time.sleep(wait_time)

        # Re-acquire lock and get token
        with self._thread_lock:
            self._refill()
            self._tokens -= 1
            return True

    async def acquire_async(self, blocking: bool = True) -> bool:
        """Acquire a token asynchronously (non-blocking sleep).

        Args:
            blocking: If True, wait for token. If False, return immediately.

        Returns:
            True if token acquired, False if non-blocking and no token available.
        """
        async_lock = self._get_async_lock()

        async with async_lock:
            # Also acquire thread lock for shared state
            with self._thread_lock:
                self._refill()

                if self._tokens >= 1:
                    self._tokens -= 1
                    return True

                if not blocking:
                    return False

                wait_time = self._calculate_wait_time()

        # Async sleep outside locks
        await asyncio.sleep(wait_time)

        # Re-acquire locks and get token
        async with async_lock:
            with self._thread_lock:
                self._refill()
                self._tokens -= 1
                return True

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (for debugging)."""
        with self._thread_lock:
            self._refill()
            return self._tokens


class DomainRateLimiter:
    """Per-domain rate limiter with shared global rate option.

    Maintains separate token buckets for each domain while optionally
    enforcing a global rate limit across all domains.
    """

    def __init__(
        self,
        default_rate: float = 2.0,
        domain_rates: dict[str, float] | None = None,
        global_rate: float | None = None,
    ):
        """Initialize domain rate limiter.

        Args:
            default_rate: Default requests/second for domains without specific rate.
                         Set to 0 to disable rate limiting.
            domain_rates: Dict mapping domain to specific rate limit.
            global_rate: Optional global rate limit across all domains.
        """
        self._default_rate = default_rate
        self._domain_rates = domain_rates or {}
        self._global_rate = global_rate

        self._buckets: dict[str, TokenBucket] = {}
        self._global_bucket: TokenBucket | None = None
        self._lock = threading.Lock()

        if global_rate and global_rate > 0:
            self._global_bucket = TokenBucket(global_rate)

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def _get_bucket(self, domain: str) -> TokenBucket | None:
        """Get or create bucket for domain. Returns None if rate limiting disabled."""
        rate = self._domain_rates.get(domain, self._default_rate)
        if rate <= 0:
            return None

        with self._lock:
            if domain not in self._buckets:
                self._buckets[domain] = TokenBucket(rate)
            return self._buckets[domain]

    def acquire_sync(self, url: str, blocking: bool = True) -> bool:
        """Acquire rate limit token for URL synchronously.

        Args:
            url: The URL being requested.
            blocking: Whether to block waiting for token.

        Returns:
            True if token acquired, False if non-blocking and rate limited.
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)

        # Check global rate first
        if self._global_bucket:
            if not self._global_bucket.acquire_sync(blocking):
                return False

        # Check domain rate
        if bucket:
            return bucket.acquire_sync(blocking)

        return True

    async def acquire_async(self, url: str, blocking: bool = True) -> bool:
        """Acquire rate limit token for URL asynchronously.

        Args:
            url: The URL being requested.
            blocking: Whether to block waiting for token.

        Returns:
            True if token acquired, False if non-blocking and rate limited.
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)

        # Check global rate first
        if self._global_bucket:
            if not await self._global_bucket.acquire_async(blocking):
                return False

        # Check domain rate
        if bucket:
            return await bucket.acquire_async(blocking)

        return True

    def set_domain_rate(self, domain: str, rate: float) -> None:
        """Set rate limit for specific domain.

        Args:
            domain: Domain name (e.g., "example.com").
            rate: Requests per second (0 to disable).
        """
        with self._lock:
            self._domain_rates[domain] = rate
            # Remove existing bucket to force recreation with new rate
            self._buckets.pop(domain, None)

    def get_domain_info(self, url: str) -> dict:
        """Get rate limiting info for URL (for debugging).

        Returns:
            Dict with domain, rate, and available tokens.
        """
        domain = self._get_domain(url)
        rate = self._domain_rates.get(domain, self._default_rate)
        bucket = self._buckets.get(domain)

        return {
            "domain": domain,
            "rate": rate,
            "tokens": bucket.available_tokens if bucket else float("inf"),
            "rate_limiting_enabled": rate > 0,
        }
