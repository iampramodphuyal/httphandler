"""Configuration dataclasses and enums for the HTTP client."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ClientConfig:
    """Configuration for ScraperClient.

    Attributes:
        mode: Operating mode - "speed" for aggressive scraping, "stealth" for
              browser-like behavior with fingerprinting.
        persist_cookies: Whether to persist cookies between requests. Default False
                        means each request starts with empty cookie jar.
        profile: Browser profile for fingerprinting (e.g., "chrome_120", "firefox_121").
        rate_limit: Requests per second per domain. 0 disables rate limiting.
        timeout: Total request timeout in seconds.
        connect_timeout: Connection establishment timeout in seconds.
        retries: Number of retry attempts on failure.
        retry_codes: HTTP status codes that trigger a retry.
        retry_backoff_base: Base for exponential backoff calculation.
        proxies: List of proxy URLs (e.g., ["socks5://host:port", "http://host:port"]).
        proxy_strategy: How to select proxies - "round_robin", "random", or "least_used".
        proxy_max_failures: Consecutive failures before disabling a proxy.
        proxy_cooldown: Seconds before re-enabling a failed proxy.
        max_workers: Thread pool size for gather_sync().
        default_concurrency: Semaphore limit for gather_async().
        min_delay: Minimum random delay in stealth mode (seconds).
        max_delay: Maximum random delay in stealth mode (seconds).
        verify_ssl: Whether to verify SSL certificates.
        follow_redirects: Whether to follow HTTP redirects.
        max_redirects: Maximum number of redirects to follow.
    """

    # Operating mode
    mode: Literal["speed", "stealth"] = "speed"

    # Session behavior
    persist_cookies: bool = False

    # Fingerprinting
    profile: str = "chrome_120"

    # Rate limiting
    rate_limit: float = 2.0  # requests per second per domain, 0 = disabled

    # Timeouts
    timeout: float = 30.0
    connect_timeout: float = 10.0

    # Retry configuration
    retries: int = 3
    retry_codes: tuple[int, ...] = (429, 500, 502, 503, 504, 520, 521, 522, 523, 524)
    retry_backoff_base: float = 2.0

    # Proxy configuration
    proxies: list[str] | None = None
    proxy_strategy: Literal["round_robin", "random", "least_used"] = "round_robin"
    proxy_max_failures: int = 3
    proxy_cooldown: float = 300.0  # 5 minutes

    # Concurrency
    max_workers: int = 10  # for gather_sync thread pool
    default_concurrency: int = 10  # for gather_async semaphore

    # Stealth mode delays
    min_delay: float = 1.0
    max_delay: float = 3.0

    # SSL and redirects
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_redirects: int = 10

    # Default headers (merged with profile headers)
    default_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.rate_limit < 0:
            raise ValueError("rate_limit must be >= 0")
        if self.timeout <= 0:
            raise ValueError("timeout must be > 0")
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be > 0")
        if self.retries < 0:
            raise ValueError("retries must be >= 0")
        if self.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if self.default_concurrency < 1:
            raise ValueError("default_concurrency must be >= 1")
        if self.min_delay < 0 or self.max_delay < 0:
            raise ValueError("delays must be >= 0")
        if self.min_delay > self.max_delay:
            raise ValueError("min_delay must be <= max_delay")
