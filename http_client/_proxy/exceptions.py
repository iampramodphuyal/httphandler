"""Proxy-related exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import ProxyConfig


class ProxyError(Exception):
    """Base exception for proxy-related errors."""

    pass


class ProxyConfigurationError(ProxyError):
    """Invalid proxy configuration."""

    def __init__(self, message: str, config: dict[str, Any] | None = None):
        super().__init__(message)
        self.config = config


class ProxyConnectionError(ProxyError):
    """Failed to connect through proxy."""

    def __init__(
        self,
        message: str,
        proxy_url: str | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.proxy_url = proxy_url
        self.original_error = original_error


class ProxyAuthenticationError(ProxyError):
    """Proxy authentication failed."""

    def __init__(self, message: str, proxy_url: str | None = None):
        super().__init__(message)
        self.proxy_url = proxy_url


class NoHealthyProxiesError(ProxyError):
    """No healthy proxies available in pool."""

    def __init__(self, message: str = "No healthy proxies available"):
        super().__init__(message)


class ProxyPoolExhaustedError(ProxyError):
    """All proxies in pool have failed."""

    def __init__(
        self,
        message: str = "All proxies in pool have failed",
        failed_proxies: list[str] | None = None,
    ):
        super().__init__(message)
        self.failed_proxies = failed_proxies or []


class ProviderNotFoundError(ProxyError):
    """Requested proxy provider not found."""

    def __init__(self, provider_name: str):
        super().__init__(f"Provider not found: {provider_name}")
        self.provider_name = provider_name
