"""Proxy configuration and health tracking models."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse


class ProxyProtocol(str, Enum):
    """Supported proxy protocols."""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyType(str, Enum):
    """Types of proxies."""

    DATACENTER = "datacenter"
    RESIDENTIAL = "residential"
    MOBILE = "mobile"
    ISP = "isp"


@dataclass
class ProxyConfig:
    """Configuration for a single proxy.

    Attributes:
        url: Full proxy URL (e.g., "http://user:pass@host:port")
        protocol: Proxy protocol (http, https, socks4, socks5)
        proxy_type: Type of proxy (datacenter, residential, etc.)
        country: Country code (e.g., "US", "GB")
        host: Proxy host
        port: Proxy port
        username: Auth username (optional)
        password: Auth password (optional)
        weight: Weight for weighted round-robin (default 1)
        tags: Custom tags for filtering
    """

    url: str
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    proxy_type: ProxyType | None = None
    country: str | None = None
    host: str = ""
    port: int = 0
    username: str | None = None
    password: str | None = None
    weight: int = 1
    tags: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Parse URL if host/port not provided."""
        if not self.host and self.url:
            self._parse_url()

    def _parse_url(self) -> None:
        """Parse proxy URL into components."""
        parsed = urlparse(self.url)
        self.host = parsed.hostname or ""
        self.port = parsed.port or 0
        self.username = parsed.username
        self.password = parsed.password
        if parsed.scheme:
            try:
                self.protocol = ProxyProtocol(parsed.scheme.lower())
            except ValueError:
                pass

    @property
    def identifier(self) -> str:
        """Unique identifier for this proxy."""
        return f"{self.host}:{self.port}"

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProxyConfig):
            return False
        return self.identifier == other.identifier


@dataclass
class ProxyHealth:
    """Health tracking for a proxy.

    Attributes:
        proxy_id: Identifier of the proxy
        consecutive_failures: Number of consecutive failures
        total_requests: Total requests made through this proxy
        total_failures: Total failures
        last_success: Timestamp of last successful request
        last_failure: Timestamp of last failure
        last_error: Last error message
        avg_response_time: Average response time in seconds
        is_healthy: Whether proxy is considered healthy
        cooldown_until: Timestamp until proxy is on cooldown
    """

    proxy_id: str
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    last_success: float | None = None
    last_failure: float | None = None
    last_error: str | None = None
    avg_response_time: float = 0.0
    is_healthy: bool = True
    cooldown_until: float | None = None
    _response_times: list[float] = field(default_factory=list)

    def record_success(self, response_time: float) -> None:
        """Record a successful request."""
        self.total_requests += 1
        self.consecutive_failures = 0
        self.last_success = time.time()
        self.is_healthy = True
        self.cooldown_until = None

        # Update response time average (keep last 10)
        self._response_times.append(response_time)
        if len(self._response_times) > 10:
            self._response_times.pop(0)
        self.avg_response_time = sum(self._response_times) / len(self._response_times)

    def record_failure(
        self,
        error: str,
        max_failures: int = 3,
        cooldown_seconds: float = 60.0,
    ) -> None:
        """Record a failed request."""
        self.total_requests += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure = time.time()
        self.last_error = error

        # Mark unhealthy and set cooldown after max failures
        if self.consecutive_failures >= max_failures:
            self.is_healthy = False
            self.cooldown_until = time.time() + cooldown_seconds

    def check_cooldown(self) -> bool:
        """Check if cooldown has expired and reset if so.

        Returns:
            True if cooldown expired and proxy was reset to healthy
        """
        if self.cooldown_until and time.time() > self.cooldown_until:
            self.cooldown_until = None
            self.is_healthy = True
            self.consecutive_failures = 0
            return True
        return False

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.total_failures) / self.total_requests


@dataclass
class ProxyPoolStats:
    """Statistics for a proxy pool.

    Attributes:
        total_proxies: Total number of proxies in pool
        healthy_proxies: Number of healthy proxies
        unhealthy_proxies: Number of unhealthy proxies
        total_requests: Total requests made
        total_failures: Total failures
        avg_response_time: Average response time across all proxies
    """

    total_proxies: int = 0
    healthy_proxies: int = 0
    unhealthy_proxies: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.total_failures) / self.total_requests
