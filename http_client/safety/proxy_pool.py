"""Thread-safe proxy pool with rotation strategies and health tracking."""

from __future__ import annotations

import copy
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse


class InvalidProxyURLError(ValueError):
    """Raised when a proxy URL is invalid."""

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Invalid proxy URL '{url}': {reason}")


# Valid proxy schemes
VALID_PROXY_SCHEMES = {"http", "https", "socks4", "socks5", "socks4a", "socks5h"}


def validate_proxy_url(url: str) -> None:
    """Validate a proxy URL.

    Args:
        url: Proxy URL to validate.

    Raises:
        InvalidProxyURLError: If the URL is invalid.
    """
    if not url or not isinstance(url, str):
        raise InvalidProxyURLError(url, "URL must be a non-empty string")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise InvalidProxyURLError(url, f"Failed to parse URL: {e}") from e

    # Check scheme
    scheme = parsed.scheme.lower()
    if not scheme:
        raise InvalidProxyURLError(url, "Missing scheme (e.g., http://, socks5://)")

    if scheme not in VALID_PROXY_SCHEMES:
        raise InvalidProxyURLError(
            url,
            f"Invalid scheme '{scheme}'. Must be one of: {', '.join(sorted(VALID_PROXY_SCHEMES))}"
        )

    # Check host
    if not parsed.hostname:
        raise InvalidProxyURLError(url, "Missing hostname")

    # Port is technically optional (defaults vary by scheme), but warn if missing
    # We don't raise an error since some proxy configs use default ports


@dataclass
class Proxy:
    """Proxy with health tracking metadata.

    Attributes:
        url: Proxy URL (e.g., "socks5://host:port", "http://user:pass@host:port").
        enabled: Whether proxy is currently active.
        consecutive_failures: Number of consecutive request failures.
        total_requests: Total requests made through this proxy.
        total_failures: Total failures through this proxy.
        last_used: Timestamp of last use.
        last_failure: Timestamp of last failure.
        disabled_until: Timestamp when proxy should be re-enabled (if disabled).
    """

    url: str
    enabled: bool = True
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    last_used: float = 0.0
    last_failure: float = 0.0
    disabled_until: float = 0.0

    @property
    def protocol(self) -> str:
        """Get proxy protocol (http, https, socks5, etc.)."""
        return urlparse(self.url).scheme.lower()

    @property
    def host(self) -> str:
        """Get proxy host."""
        return urlparse(self.url).hostname or ""

    @property
    def port(self) -> int | None:
        """Get proxy port."""
        return urlparse(self.url).port

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0-1.0)."""
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.total_failures) / self.total_requests

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.consecutive_failures = 0
        self.total_requests = 0
        self.total_failures = 0
        self.last_used = 0.0
        self.last_failure = 0.0


class ProxyPool:
    """Thread-safe proxy pool with rotation strategies and auto-recovery.

    Supports three rotation strategies:
    - round_robin: Cycle through proxies in order
    - random: Select randomly from available proxies
    - least_used: Select proxy with oldest last_used timestamp
    """

    def __init__(
        self,
        proxies: list[str] | None = None,
        strategy: Literal["round_robin", "random", "least_used"] = "round_robin",
        max_failures: int = 3,
        cooldown: float = 300.0,
    ):
        """Initialize proxy pool.

        Args:
            proxies: List of proxy URLs.
            strategy: Rotation strategy.
            max_failures: Consecutive failures before disabling a proxy.
            cooldown: Seconds before re-enabling a disabled proxy.
        """
        self._strategy = strategy
        self._max_failures = max_failures
        self._cooldown = cooldown
        self._lock = threading.Lock()
        self._round_robin_index = 0

        self._proxies: list[Proxy] = []
        if proxies:
            for url in proxies:
                validate_proxy_url(url)  # Fail fast on invalid URLs
                self._proxies.append(Proxy(url=url))

    def add_proxy(self, url: str) -> None:
        """Add a proxy to the pool.

        Args:
            url: Proxy URL to add.

        Raises:
            InvalidProxyURLError: If the URL is invalid.
        """
        validate_proxy_url(url)  # Validate before acquiring lock
        with self._lock:
            # Don't add duplicates
            if not any(p.url == url for p in self._proxies):
                self._proxies.append(Proxy(url=url))

    def remove_proxy(self, url: str) -> bool:
        """Remove a proxy from the pool.

        Args:
            url: Proxy URL to remove.

        Returns:
            True if proxy was removed, False if not found.
        """
        with self._lock:
            for i, proxy in enumerate(self._proxies):
                if proxy.url == url:
                    self._proxies.pop(i)
                    return True
            return False

    def _check_recovery(self) -> None:
        """Check and re-enable proxies past cooldown period. Must be called under lock."""
        now = time.monotonic()
        for proxy in self._proxies:
            if not proxy.enabled and proxy.disabled_until <= now:
                proxy.enabled = True
                proxy.consecutive_failures = 0

    def _get_available_proxies(self) -> list[Proxy]:
        """Get list of enabled proxies. Must be called under lock."""
        self._check_recovery()
        return [p for p in self._proxies if p.enabled]

    def get_proxy(self) -> Proxy | None:
        """Get next proxy according to strategy.

        Returns a shallow copy of the Proxy to prevent concurrent modification
        issues. The caller should use proxy.url for report_success/report_failure.

        Returns:
            Copy of Proxy object or None if no proxies available.
        """
        with self._lock:
            available = self._get_available_proxies()
            if not available:
                return None

            if self._strategy == "round_robin":
                proxy = available[self._round_robin_index % len(available)]
                self._round_robin_index = (self._round_robin_index + 1) % len(available)

            elif self._strategy == "random":
                proxy = random.choice(available)

            elif self._strategy == "least_used":
                proxy = min(available, key=lambda p: p.last_used)

            else:
                proxy = available[0]

            proxy.last_used = time.monotonic()
            proxy.total_requests += 1

            # Return a copy to prevent concurrent modification issues.
            # Caller uses proxy.url for report_success/report_failure lookups.
            return copy.copy(proxy)

    def report_success(self, proxy_url: str) -> None:
        """Report successful request through proxy.

        Args:
            proxy_url: URL of the proxy that succeeded.
        """
        with self._lock:
            for proxy in self._proxies:
                if proxy.url == proxy_url:
                    proxy.consecutive_failures = 0
                    break

    def report_failure(self, proxy_url: str) -> None:
        """Report failed request through proxy.

        Args:
            proxy_url: URL of the proxy that failed.
        """
        with self._lock:
            for proxy in self._proxies:
                if proxy.url == proxy_url:
                    proxy.consecutive_failures += 1
                    proxy.total_failures += 1
                    proxy.last_failure = time.monotonic()

                    if proxy.consecutive_failures >= self._max_failures:
                        proxy.enabled = False
                        proxy.disabled_until = time.monotonic() + self._cooldown
                    break

    def force_disable(self, proxy_url: str) -> None:
        """Forcefully disable a proxy.

        Args:
            proxy_url: URL of the proxy to disable.
        """
        with self._lock:
            for proxy in self._proxies:
                if proxy.url == proxy_url:
                    proxy.enabled = False
                    proxy.disabled_until = time.monotonic() + self._cooldown
                    break

    def force_enable(self, proxy_url: str) -> None:
        """Forcefully enable a proxy.

        Args:
            proxy_url: URL of the proxy to enable.
        """
        with self._lock:
            for proxy in self._proxies:
                if proxy.url == proxy_url:
                    proxy.enabled = True
                    proxy.consecutive_failures = 0
                    proxy.disabled_until = 0.0
                    break

    def reset_all(self) -> None:
        """Reset all proxies to initial state."""
        with self._lock:
            for proxy in self._proxies:
                proxy.enabled = True
                proxy.reset_stats()
            self._round_robin_index = 0

    @property
    def available_count(self) -> int:
        """Get count of currently available proxies."""
        with self._lock:
            return len(self._get_available_proxies())

    @property
    def total_count(self) -> int:
        """Get total count of proxies in pool."""
        with self._lock:
            return len(self._proxies)

    @property
    def has_proxies(self) -> bool:
        """Check if pool has any proxies configured."""
        with self._lock:
            return len(self._proxies) > 0

    def get_stats(self) -> dict:
        """Get pool statistics.

        Returns:
            Dict with pool statistics.
        """
        with self._lock:
            available = self._get_available_proxies()
            return {
                "total": len(self._proxies),
                "available": len(available),
                "disabled": len(self._proxies) - len(available),
                "strategy": self._strategy,
                "proxies": [
                    {
                        "url": p.url,
                        "enabled": p.enabled,
                        "consecutive_failures": p.consecutive_failures,
                        "success_rate": p.success_rate,
                    }
                    for p in self._proxies
                ],
            }

    def __len__(self) -> int:
        """Return total number of proxies."""
        return self.total_count

    def __bool__(self) -> bool:
        """Return True if pool has any proxies."""
        return self.has_proxies
