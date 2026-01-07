"""Proxy pool management with rotation and health tracking."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from .base import ProxyProvider
from .exceptions import NoHealthyProxiesError, ProviderNotFoundError
from .models import ProxyConfig, ProxyHealth, ProxyPoolStats, ProxyProtocol, ProxyType


class ProxyManager:
    """Thread-safe and async-safe proxy pool manager.

    Features:
    - Multiple provider support
    - Round-robin rotation with health tracking
    - Automatic failover on proxy failure
    - Cooldown period for failed proxies
    - Statistics and monitoring

    Example:
        from http_client._proxy import ProxyManager, GenericProvider

        # Create manager
        manager = ProxyManager()

        # Add provider
        provider = GenericProvider(proxies=["http://proxy1:8080", "http://proxy2:8080"])
        manager.add_provider(provider)

        # Set active proxy
        manager.set_proxy(provider="generic", country="US")

        # Get current proxy URL
        url = manager.get_current_proxy()

        # Switch to next proxy (rotation)
        manager.switch_proxy()
    """

    def __init__(
        self,
        max_failures: int = 3,
        cooldown_seconds: float = 60.0,
    ):
        """Initialize proxy manager.

        Args:
            max_failures: Failures before marking proxy unhealthy
            cooldown_seconds: Cooldown period for unhealthy proxies
        """
        self._max_failures = max_failures
        self._cooldown_seconds = cooldown_seconds

        # Provider registry
        self._providers: dict[str, ProxyProvider] = {}

        # Proxy pool (all active proxies)
        self._pool: list[ProxyConfig] = []

        # Health tracking
        self._health: dict[str, ProxyHealth] = {}

        # Current state
        self._current_index: int = 0
        self._current_proxy: ProxyConfig | None = None
        self._active_provider: str | None = None

        # Filters
        self._filter_country: str | None = None
        self._filter_type: ProxyType | None = None
        self._filter_protocol: ProxyProtocol = ProxyProtocol.HTTP

        # Thread safety (dual-lock pattern from CookieStore)
        self._thread_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazily initialize async lock within event loop context."""
        with self._thread_lock:
            if self._async_lock is None:
                try:
                    self._async_lock = asyncio.Lock()
                except RuntimeError as e:
                    raise RuntimeError(
                        "Cannot create asyncio.Lock outside of async context."
                    ) from e
            return self._async_lock

    # ========== Provider Management ==========

    def add_provider(self, provider: ProxyProvider) -> None:
        """Add a proxy provider.

        Args:
            provider: ProxyProvider instance
        """
        with self._thread_lock:
            self._providers[provider.name] = provider

    def remove_provider(self, name: str) -> bool:
        """Remove a provider by name.

        Returns:
            True if provider was found and removed
        """
        with self._thread_lock:
            if name in self._providers:
                del self._providers[name]
                # Clear pool if active provider was removed
                if self._active_provider == name:
                    self._pool.clear()
                    self._current_proxy = None
                    self._active_provider = None
                return True
            return False

    def get_provider(self, name: str) -> ProxyProvider:
        """Get provider by name.

        Raises:
            ProviderNotFoundError: If provider not found
        """
        with self._thread_lock:
            if name not in self._providers:
                raise ProviderNotFoundError(name)
            return self._providers[name]

    def list_providers(self) -> list[str]:
        """Get list of registered provider names."""
        with self._thread_lock:
            return list(self._providers.keys())

    # ========== Proxy Selection ==========

    def set_proxy(
        self,
        provider: str,
        proxy_type: str | ProxyType | None = None,
        country: str | None = None,
        protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
        count: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Set active proxy from provider.

        Fetches proxies from provider and sets up rotation pool.

        Args:
            provider: Provider name
            proxy_type: Type of proxy (datacenter, residential, etc.)
            country: Country code (e.g., "US", "GB")
            protocol: Proxy protocol (http, https, socks5)
            count: Number of proxies to fetch for rotation
            **kwargs: Provider-specific options
        """
        with self._thread_lock:
            self._set_proxy_unlocked(
                provider, proxy_type, country, protocol, count, **kwargs
            )

    def _set_proxy_unlocked(
        self,
        provider: str,
        proxy_type: str | ProxyType | None,
        country: str | None,
        protocol: str | ProxyProtocol,
        count: int | None,
        **kwargs: Any,
    ) -> None:
        """Set proxy without acquiring lock (must be called under lock)."""
        if provider not in self._providers:
            raise ProviderNotFoundError(provider)

        prov = self._providers[provider]

        # Store filters
        self._filter_country = country
        if isinstance(proxy_type, str):
            self._filter_type = ProxyType(proxy_type.lower())
        else:
            self._filter_type = proxy_type
        if isinstance(protocol, str):
            self._filter_protocol = ProxyProtocol(protocol.lower())
        else:
            self._filter_protocol = protocol

        # Fetch proxies
        if count and count > 1:
            proxies = prov.get_proxies(
                count=count,
                proxy_type=proxy_type,
                country=country,
                protocol=protocol,
                **kwargs,
            )
        else:
            proxies = [
                prov.get_proxy(
                    proxy_type=proxy_type,
                    country=country,
                    protocol=protocol,
                    **kwargs,
                )
            ]

        # Set up pool
        self._pool = proxies
        self._current_index = 0
        self._current_proxy = proxies[0] if proxies else None
        self._active_provider = provider

        # Initialize health tracking for new proxies
        for proxy in proxies:
            if proxy.identifier not in self._health:
                self._health[proxy.identifier] = ProxyHealth(proxy_id=proxy.identifier)

    async def set_proxy_async(
        self,
        provider: str,
        proxy_type: str | ProxyType | None = None,
        country: str | None = None,
        protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
        count: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Set active proxy from provider (async version)."""
        async_lock = self._get_async_lock()
        async with async_lock:
            with self._thread_lock:
                self._set_proxy_unlocked(
                    provider, proxy_type, country, protocol, count, **kwargs
                )

    def reset_proxy(self) -> None:
        """Remove proxy configuration (disable proxy)."""
        with self._thread_lock:
            self._pool.clear()
            self._current_proxy = None
            self._current_index = 0
            self._active_provider = None
            self._filter_country = None
            self._filter_type = None

    async def reset_proxy_async(self) -> None:
        """Remove proxy configuration (async version)."""
        async_lock = self._get_async_lock()
        async with async_lock:
            with self._thread_lock:
                self._pool.clear()
                self._current_proxy = None
                self._current_index = 0
                self._active_provider = None
                self._filter_country = None
                self._filter_type = None

    def switch_proxy(self) -> ProxyConfig | None:
        """Rotate to next healthy proxy in pool.

        Uses round-robin rotation, skipping unhealthy proxies.

        Returns:
            New current proxy, or None if no proxies in pool

        Raises:
            NoHealthyProxiesError: If no healthy proxies available
        """
        with self._thread_lock:
            return self._switch_proxy_unlocked()

    def _switch_proxy_unlocked(self) -> ProxyConfig | None:
        """Switch proxy without acquiring lock (must be called under lock)."""
        if not self._pool:
            return None

        # Check cooldowns and find next healthy proxy
        healthy = self._get_healthy_proxies_unlocked()

        if not healthy:
            raise NoHealthyProxiesError()

        # Find next proxy after current index
        pool_size = len(self._pool)
        start_index = (self._current_index + 1) % pool_size

        for i in range(pool_size):
            idx = (start_index + i) % pool_size
            proxy = self._pool[idx]
            if proxy in healthy:
                self._current_index = idx
                self._current_proxy = proxy
                return proxy

        # Should not reach here if healthy list is not empty
        raise NoHealthyProxiesError()

    async def switch_proxy_async(self) -> ProxyConfig | None:
        """Rotate to next healthy proxy (async version)."""
        async_lock = self._get_async_lock()
        async with async_lock:
            with self._thread_lock:
                return self._switch_proxy_unlocked()

    def _get_healthy_proxies_unlocked(self) -> list[ProxyConfig]:
        """Get list of healthy proxies (must be called under lock)."""
        healthy = []
        for proxy in self._pool:
            health = self._health.get(proxy.identifier)
            if health:
                # Check if cooldown expired
                health.check_cooldown()
                if health.is_healthy:
                    healthy.append(proxy)
            else:
                # No health record = healthy
                healthy.append(proxy)
        return healthy

    # ========== Proxy Access ==========

    def get_current_proxy(self) -> str | None:
        """Get current proxy URL for requests.

        Returns:
            Proxy URL string or None if no proxy set
        """
        with self._thread_lock:
            return self._current_proxy.url if self._current_proxy else None

    async def get_current_proxy_async(self) -> str | None:
        """Get current proxy URL (async version)."""
        async_lock = self._get_async_lock()
        async with async_lock:
            with self._thread_lock:
                return self._current_proxy.url if self._current_proxy else None

    def get_current_config(self) -> ProxyConfig | None:
        """Get current proxy configuration."""
        with self._thread_lock:
            return self._current_proxy

    # ========== Health Tracking ==========

    def record_success(self, proxy_url: str | None, response_time: float) -> None:
        """Record successful request through proxy.

        Args:
            proxy_url: Proxy URL (or None if no proxy)
            response_time: Request duration in seconds
        """
        if not proxy_url:
            return

        with self._thread_lock:
            # Find proxy by URL
            for proxy in self._pool:
                if proxy.url == proxy_url:
                    health = self._health.get(proxy.identifier)
                    if health:
                        health.record_success(response_time)
                    break

    async def record_success_async(
        self, proxy_url: str | None, response_time: float
    ) -> None:
        """Record successful request (async version)."""
        if not proxy_url:
            return

        async_lock = self._get_async_lock()
        async with async_lock:
            with self._thread_lock:
                for proxy in self._pool:
                    if proxy.url == proxy_url:
                        health = self._health.get(proxy.identifier)
                        if health:
                            health.record_success(response_time)
                        break

    def record_failure(self, proxy_url: str | None, error: str) -> None:
        """Record failed request through proxy.

        Args:
            proxy_url: Proxy URL (or None if no proxy)
            error: Error message
        """
        if not proxy_url:
            return

        with self._thread_lock:
            for proxy in self._pool:
                if proxy.url == proxy_url:
                    health = self._health.get(proxy.identifier)
                    if health:
                        health.record_failure(
                            error,
                            max_failures=self._max_failures,
                            cooldown_seconds=self._cooldown_seconds,
                        )
                    break

    async def record_failure_async(self, proxy_url: str | None, error: str) -> None:
        """Record failed request (async version)."""
        if not proxy_url:
            return

        async_lock = self._get_async_lock()
        async with async_lock:
            with self._thread_lock:
                for proxy in self._pool:
                    if proxy.url == proxy_url:
                        health = self._health.get(proxy.identifier)
                        if health:
                            health.record_failure(
                                error,
                                max_failures=self._max_failures,
                                cooldown_seconds=self._cooldown_seconds,
                            )
                        break

    def get_health(self, proxy_url: str) -> ProxyHealth | None:
        """Get health info for a proxy."""
        with self._thread_lock:
            for proxy in self._pool:
                if proxy.url == proxy_url:
                    return self._health.get(proxy.identifier)
            return None

    # ========== Statistics ==========

    def get_stats(self) -> ProxyPoolStats:
        """Get pool statistics."""
        with self._thread_lock:
            healthy = self._get_healthy_proxies_unlocked()

            total_requests = 0
            total_failures = 0
            response_times = []

            for health in self._health.values():
                total_requests += health.total_requests
                total_failures += health.total_failures
                if health.avg_response_time > 0:
                    response_times.append(health.avg_response_time)

            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else 0.0
            )

            return ProxyPoolStats(
                total_proxies=len(self._pool),
                healthy_proxies=len(healthy),
                unhealthy_proxies=len(self._pool) - len(healthy),
                total_requests=total_requests,
                total_failures=total_failures,
                avg_response_time=avg_response_time,
            )

    # ========== Pool Info ==========

    @property
    def pool_size(self) -> int:
        """Number of proxies in pool."""
        with self._thread_lock:
            return len(self._pool)

    @property
    def has_proxy(self) -> bool:
        """Check if a proxy is currently set."""
        with self._thread_lock:
            return self._current_proxy is not None

    @property
    def active_provider_name(self) -> str | None:
        """Name of currently active provider."""
        with self._thread_lock:
            return self._active_provider
