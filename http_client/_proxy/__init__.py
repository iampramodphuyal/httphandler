"""Proxy management for HTTPClient."""

from .base import ProxyProvider
from .exceptions import (
    NoHealthyProxiesError,
    ProviderNotFoundError,
    ProxyAuthenticationError,
    ProxyConfigurationError,
    ProxyConnectionError,
    ProxyError,
    ProxyPoolExhaustedError,
)
from .manager import ProxyManager
from .models import (
    ProxyConfig,
    ProxyHealth,
    ProxyPoolStats,
    ProxyProtocol,
    ProxyType,
)
from .providers.generic import GenericProvider

__all__ = [
    # Models
    "ProxyProtocol",
    "ProxyType",
    "ProxyConfig",
    "ProxyHealth",
    "ProxyPoolStats",
    # Exceptions
    "ProxyError",
    "ProxyConfigurationError",
    "ProxyConnectionError",
    "ProxyAuthenticationError",
    "NoHealthyProxiesError",
    "ProxyPoolExhaustedError",
    "ProviderNotFoundError",
    # Base class
    "ProxyProvider",
    # Providers
    "GenericProvider",
    # Manager
    "ProxyManager",
]
