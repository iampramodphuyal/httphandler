"""Abstract base class for proxy providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import ProxyConfig, ProxyProtocol, ProxyType


class ProxyProvider(ABC):
    """Abstract base class for proxy providers.

    Implement this class to add support for new proxy services
    (BrightData, Oxylabs, SmartProxy, etc.)

    Example:
        class BrightDataProvider(ProxyProvider):
            def __init__(self, username: str, password: str):
                self._username = username
                self._password = password

            @property
            def name(self) -> str:
                return "brightdata"

            def get_proxy(
                self,
                proxy_type: str | ProxyType | None = None,
                country: str | None = None,
                protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
                **kwargs
            ) -> ProxyConfig:
                # Build BrightData proxy URL
                zone = kwargs.get("zone", "datacenter")
                host = "brd.superproxy.io"
                port = 22225
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier (e.g., 'generic', 'brightdata')."""
        pass

    @abstractmethod
    def get_proxy(
        self,
        proxy_type: str | ProxyType | None = None,
        country: str | None = None,
        protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
        **kwargs: Any,
    ) -> ProxyConfig:
        """Get a single proxy matching the criteria.

        Args:
            proxy_type: Type of proxy (datacenter, residential, etc.)
            country: Country code (e.g., "US", "GB")
            protocol: Proxy protocol (http, https, socks5)
            **kwargs: Provider-specific options

        Returns:
            ProxyConfig for the proxy

        Raises:
            ProxyConfigurationError: If proxy cannot be configured
        """
        pass

    @abstractmethod
    def get_proxies(
        self,
        count: int = 1,
        proxy_type: str | ProxyType | None = None,
        country: str | None = None,
        protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
        **kwargs: Any,
    ) -> list[ProxyConfig]:
        """Get multiple proxies matching the criteria.

        Args:
            count: Number of proxies to return
            proxy_type: Type of proxy
            country: Country code
            protocol: Proxy protocol
            **kwargs: Provider-specific options

        Returns:
            List of ProxyConfig objects
        """
        pass

    def validate_credentials(self) -> bool:
        """Validate provider credentials.

        Override this method to implement credential validation
        for providers that support it.

        Returns:
            True if credentials are valid
        """
        return True

    def get_usage(self) -> dict[str, Any]:
        """Get usage statistics from provider.

        Override this method for providers that offer usage APIs.

        Returns:
            Dict with usage info (e.g., bandwidth used, requests made)
        """
        return {}

    def refresh_proxies(self) -> None:
        """Refresh proxy list from provider.

        Override this method for providers that support
        fetching fresh proxy lists.
        """
        pass
