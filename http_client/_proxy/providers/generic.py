"""Generic proxy provider for custom proxy URLs."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from ..base import ProxyProvider
from ..exceptions import ProxyConfigurationError
from ..models import ProxyConfig, ProxyProtocol, ProxyType


class GenericProvider(ProxyProvider):
    """Provider for user-supplied proxy URLs.

    Allows users to use their own proxy servers or services
    by providing proxy URLs directly.

    Example:
        # Single proxy
        provider = GenericProvider(
            proxies=["http://user:pass@proxy1.example.com:8080"]
        )

        # Multiple proxies with metadata
        provider = GenericProvider(
            proxies=[
                {"url": "http://proxy1:8080", "country": "US"},
                {"url": "http://proxy2:8080", "country": "GB"},
            ]
        )

        # From endpoint URL (provider fetches list)
        provider = GenericProvider(
            endpoint="https://api.example.com/proxies"
        )
    """

    def __init__(
        self,
        proxies: list[str | dict[str, Any]] | None = None,
        endpoint: str | None = None,
        endpoint_auth: dict[str, str] | None = None,
    ):
        """Initialize generic provider.

        Args:
            proxies: List of proxy URLs or config dicts
            endpoint: URL to fetch proxy list from
            endpoint_auth: Authentication for endpoint (headers)

        Raises:
            ProxyConfigurationError: If proxies cannot be loaded
        """
        self._proxy_configs: list[ProxyConfig] = []
        self._endpoint = endpoint
        self._endpoint_auth = endpoint_auth

        if proxies:
            self._load_proxies(proxies)
        elif endpoint:
            self._fetch_from_endpoint()

    @property
    def name(self) -> str:
        return "generic"

    def _load_proxies(self, proxies: list[str | dict[str, Any]]) -> None:
        """Load proxies from list."""
        for proxy in proxies:
            if isinstance(proxy, str):
                self._proxy_configs.append(ProxyConfig(url=proxy))
            elif isinstance(proxy, dict):
                self._proxy_configs.append(self._dict_to_config(proxy))
            else:
                raise ProxyConfigurationError(f"Invalid proxy format: {type(proxy)}")

    def _dict_to_config(self, data: dict[str, Any]) -> ProxyConfig:
        """Convert dict to ProxyConfig."""
        url = data.get("url")
        if not url:
            raise ProxyConfigurationError("Proxy URL is required", config=data)

        protocol = ProxyProtocol.HTTP
        if proto := data.get("protocol"):
            try:
                protocol = ProxyProtocol(proto.lower())
            except ValueError:
                pass

        proxy_type = None
        if ptype := data.get("proxy_type"):
            try:
                proxy_type = ProxyType(ptype.lower())
            except ValueError:
                pass

        return ProxyConfig(
            url=url,
            protocol=protocol,
            proxy_type=proxy_type,
            country=data.get("country"),
            weight=data.get("weight", 1),
            tags=set(data.get("tags", [])),
        )

    def _fetch_from_endpoint(self) -> None:
        """Fetch proxy list from endpoint URL."""
        if not self._endpoint:
            return

        headers: dict[str, str] = {}
        if self._endpoint_auth:
            headers.update(self._endpoint_auth)

        req = urllib.request.Request(self._endpoint, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                if isinstance(data, list):
                    self._load_proxies(data)
                elif isinstance(data, dict) and "proxies" in data:
                    self._load_proxies(data["proxies"])
        except Exception as e:
            raise ProxyConfigurationError(
                f"Failed to fetch proxies from endpoint: {e}"
            ) from e

    def add_proxy(
        self,
        url: str,
        protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
        proxy_type: str | ProxyType | None = None,
        country: str | None = None,
        weight: int = 1,
        tags: set[str] | None = None,
    ) -> None:
        """Add a proxy to the provider.

        Args:
            url: Proxy URL
            protocol: Proxy protocol
            proxy_type: Type of proxy
            country: Country code
            weight: Weight for rotation
            tags: Custom tags
        """
        if isinstance(protocol, str):
            protocol = ProxyProtocol(protocol.lower())
        if isinstance(proxy_type, str):
            proxy_type = ProxyType(proxy_type.lower())

        config = ProxyConfig(
            url=url,
            protocol=protocol,
            proxy_type=proxy_type,
            country=country,
            weight=weight,
            tags=tags or set(),
        )
        self._proxy_configs.append(config)

    def remove_proxy(self, url: str) -> bool:
        """Remove a proxy by URL.

        Returns:
            True if proxy was found and removed
        """
        for i, config in enumerate(self._proxy_configs):
            if config.url == url:
                self._proxy_configs.pop(i)
                return True
        return False

    def get_proxy(
        self,
        proxy_type: str | ProxyType | None = None,
        country: str | None = None,
        protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
        **kwargs: Any,
    ) -> ProxyConfig:
        """Get a proxy matching criteria."""
        proxies = self.get_proxies(
            count=1,
            proxy_type=proxy_type,
            country=country,
            protocol=protocol,
            **kwargs,
        )
        if not proxies:
            raise ProxyConfigurationError("No proxy matches the specified criteria")
        return proxies[0]

    def get_proxies(
        self,
        count: int = 1,
        proxy_type: str | ProxyType | None = None,
        country: str | None = None,
        protocol: str | ProxyProtocol = ProxyProtocol.HTTP,
        **kwargs: Any,
    ) -> list[ProxyConfig]:
        """Get proxies matching criteria."""
        if isinstance(proxy_type, str):
            proxy_type = ProxyType(proxy_type.lower())
        if isinstance(protocol, str):
            protocol = ProxyProtocol(protocol.lower())

        # Filter proxies
        filtered = []
        for config in self._proxy_configs:
            # Filter by proxy_type if specified
            if proxy_type and config.proxy_type and config.proxy_type != proxy_type:
                continue
            # Filter by country if specified
            if (
                country
                and config.country
                and config.country.upper() != country.upper()
            ):
                continue
            # Filter by protocol
            if config.protocol != protocol:
                continue
            filtered.append(config)

        # If no filters matched, return all with matching protocol
        if not filtered and not proxy_type and not country:
            filtered = [c for c in self._proxy_configs if c.protocol == protocol]

        # If still no matches, return all proxies
        if not filtered:
            filtered = list(self._proxy_configs)

        return filtered[:count]

    def refresh_proxies(self) -> None:
        """Refresh proxies from endpoint if configured."""
        if self._endpoint:
            self._proxy_configs.clear()
            self._fetch_from_endpoint()

    @property
    def proxy_count(self) -> int:
        """Number of proxies in provider."""
        return len(self._proxy_configs)

    @property
    def all_proxies(self) -> list[ProxyConfig]:
        """Get all configured proxies."""
        return list(self._proxy_configs)
