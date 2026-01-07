"""Tests for the proxy management module."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from http_client._proxy import (
    GenericProvider,
    NoHealthyProxiesError,
    ProviderNotFoundError,
    ProxyConfig,
    ProxyConfigurationError,
    ProxyError,
    ProxyHealth,
    ProxyManager,
    ProxyPoolStats,
    ProxyProtocol,
    ProxyProvider,
    ProxyType,
)


# ========== Model Tests ==========


class TestProxyProtocol:
    def test_protocol_values(self):
        assert ProxyProtocol.HTTP.value == "http"
        assert ProxyProtocol.HTTPS.value == "https"
        assert ProxyProtocol.SOCKS4.value == "socks4"
        assert ProxyProtocol.SOCKS5.value == "socks5"


class TestProxyType:
    def test_type_values(self):
        assert ProxyType.DATACENTER.value == "datacenter"
        assert ProxyType.RESIDENTIAL.value == "residential"
        assert ProxyType.MOBILE.value == "mobile"
        assert ProxyType.ISP.value == "isp"


class TestProxyConfig:
    def test_from_url(self):
        config = ProxyConfig(url="http://user:pass@proxy.example.com:8080")
        assert config.host == "proxy.example.com"
        assert config.port == 8080
        assert config.username == "user"
        assert config.password == "pass"
        assert config.protocol == ProxyProtocol.HTTP

    def test_from_socks5_url(self):
        config = ProxyConfig(url="socks5://localhost:1080")
        assert config.host == "localhost"
        assert config.port == 1080
        assert config.protocol == ProxyProtocol.SOCKS5

    def test_identifier(self):
        config = ProxyConfig(url="http://proxy:8080")
        assert config.identifier == "proxy:8080"

    def test_equality(self):
        config1 = ProxyConfig(url="http://proxy:8080")
        config2 = ProxyConfig(url="http://different:8080", host="proxy", port=8080)
        # They have the same identifier
        assert config1.identifier == "proxy:8080"

    def test_hash(self):
        config = ProxyConfig(url="http://proxy:8080")
        config_set = {config}
        assert len(config_set) == 1


class TestProxyHealth:
    def test_initial_state(self):
        health = ProxyHealth(proxy_id="proxy:8080")
        assert health.is_healthy
        assert health.consecutive_failures == 0
        assert health.total_requests == 0
        assert health.success_rate == 1.0

    def test_record_success(self):
        health = ProxyHealth(proxy_id="proxy:8080")
        health.record_success(0.5)
        assert health.total_requests == 1
        assert health.consecutive_failures == 0
        assert health.avg_response_time == 0.5

    def test_record_failure(self):
        health = ProxyHealth(proxy_id="proxy:8080")
        health.record_failure("Connection refused", max_failures=3)
        assert health.consecutive_failures == 1
        assert health.is_healthy  # Still healthy after 1 failure

    def test_mark_unhealthy_after_max_failures(self):
        health = ProxyHealth(proxy_id="proxy:8080")
        for i in range(3):
            health.record_failure("Connection refused", max_failures=3)
        assert not health.is_healthy
        assert health.cooldown_until is not None

    def test_cooldown_recovery(self):
        health = ProxyHealth(proxy_id="proxy:8080")
        # Mark unhealthy
        for i in range(3):
            health.record_failure("Error", max_failures=3, cooldown_seconds=0.1)
        assert not health.is_healthy

        # Wait for cooldown
        time.sleep(0.15)
        recovered = health.check_cooldown()
        assert recovered
        assert health.is_healthy
        assert health.consecutive_failures == 0

    def test_success_resets_failure_count(self):
        health = ProxyHealth(proxy_id="proxy:8080")
        health.record_failure("Error", max_failures=3)
        health.record_failure("Error", max_failures=3)
        assert health.consecutive_failures == 2
        health.record_success(0.5)
        assert health.consecutive_failures == 0
        assert health.is_healthy

    def test_success_rate(self):
        health = ProxyHealth(proxy_id="proxy:8080")
        health.record_success(0.5)
        health.record_success(0.5)
        health.record_failure("Error", max_failures=10)
        assert health.success_rate == pytest.approx(2 / 3)


class TestProxyPoolStats:
    def test_initial_state(self):
        stats = ProxyPoolStats()
        assert stats.total_proxies == 0
        assert stats.success_rate == 1.0

    def test_success_rate(self):
        stats = ProxyPoolStats(total_requests=10, total_failures=3)
        assert stats.success_rate == 0.7


# ========== GenericProvider Tests ==========


class TestGenericProvider:
    def test_init_with_url_list(self):
        provider = GenericProvider(
            proxies=["http://proxy1:8080", "http://proxy2:8080"]
        )
        assert provider.proxy_count == 2
        assert provider.name == "generic"

    def test_init_with_dict_list(self):
        provider = GenericProvider(
            proxies=[
                {"url": "http://proxy1:8080", "country": "US"},
                {"url": "http://proxy2:8080", "country": "GB"},
            ]
        )
        assert provider.proxy_count == 2
        proxies = provider.all_proxies
        assert proxies[0].country == "US"
        assert proxies[1].country == "GB"

    def test_get_proxy(self):
        provider = GenericProvider(proxies=["http://proxy1:8080"])
        proxy = provider.get_proxy()
        assert proxy.url == "http://proxy1:8080"

    def test_get_proxies(self):
        provider = GenericProvider(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        )
        proxies = provider.get_proxies(count=2)
        assert len(proxies) == 2

    def test_filter_by_country(self):
        provider = GenericProvider(
            proxies=[
                {"url": "http://p1:8080", "country": "US"},
                {"url": "http://p2:8080", "country": "GB"},
                {"url": "http://p3:8080", "country": "US"},
            ]
        )
        proxies = provider.get_proxies(count=10, country="US")
        assert len(proxies) == 2
        assert all(p.country == "US" for p in proxies)

    def test_filter_by_protocol(self):
        provider = GenericProvider(
            proxies=[
                {"url": "http://p1:8080"},
                {"url": "socks5://p2:1080", "protocol": "socks5"},
            ]
        )
        proxies = provider.get_proxies(protocol="socks5")
        assert len(proxies) == 1
        assert proxies[0].protocol == ProxyProtocol.SOCKS5

    def test_add_proxy(self):
        provider = GenericProvider()
        assert provider.proxy_count == 0
        provider.add_proxy("http://newproxy:8080", country="US")
        assert provider.proxy_count == 1
        assert provider.all_proxies[0].country == "US"

    def test_remove_proxy(self):
        provider = GenericProvider(proxies=["http://p1:8080", "http://p2:8080"])
        assert provider.proxy_count == 2
        removed = provider.remove_proxy("http://p1:8080")
        assert removed
        assert provider.proxy_count == 1

    def test_remove_nonexistent_proxy(self):
        provider = GenericProvider(proxies=["http://p1:8080"])
        removed = provider.remove_proxy("http://nonexistent:8080")
        assert not removed

    def test_no_proxies_raises(self):
        provider = GenericProvider()  # Empty provider
        with pytest.raises(ProxyConfigurationError):
            provider.get_proxy()  # No proxies at all

    def test_fallback_when_no_filter_match(self):
        # When country filter doesn't match any proxy, falls back to all proxies
        provider = GenericProvider(proxies=["http://p1:8080"])
        proxy = provider.get_proxy(country="ZZ")  # Proxy has no country, so it's included
        assert proxy.url == "http://p1:8080"


# ========== ProxyManager Tests ==========


class TestProxyManager:
    def test_init_defaults(self):
        manager = ProxyManager()
        assert manager.pool_size == 0
        assert not manager.has_proxy

    def test_add_provider(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        assert "generic" in manager.list_providers()

    def test_get_provider(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        retrieved = manager.get_provider("generic")
        assert retrieved is provider

    def test_get_nonexistent_provider_raises(self):
        manager = ProxyManager()
        with pytest.raises(ProviderNotFoundError):
            manager.get_provider("nonexistent")

    def test_remove_provider(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        removed = manager.remove_provider("generic")
        assert removed
        assert "generic" not in manager.list_providers()

    def test_set_proxy(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080", "http://p2:8080"])
        manager.add_provider(provider)
        manager.set_proxy(provider="generic")
        assert manager.has_proxy
        assert manager.get_current_proxy() == "http://p1:8080"

    def test_set_proxy_with_count(self):
        manager = ProxyManager()
        provider = GenericProvider(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        )
        manager.add_provider(provider)
        manager.set_proxy(provider="generic", count=2)
        assert manager.pool_size == 2

    def test_reset_proxy(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        manager.set_proxy(provider="generic")
        assert manager.has_proxy
        manager.reset_proxy()
        assert not manager.has_proxy
        assert manager.get_current_proxy() is None

    def test_switch_proxy_round_robin(self):
        manager = ProxyManager()
        provider = GenericProvider(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        )
        manager.add_provider(provider)
        manager.set_proxy(provider="generic", count=3)

        assert manager.get_current_proxy() == "http://p1:8080"
        manager.switch_proxy()
        assert manager.get_current_proxy() == "http://p2:8080"
        manager.switch_proxy()
        assert manager.get_current_proxy() == "http://p3:8080"
        manager.switch_proxy()
        assert manager.get_current_proxy() == "http://p1:8080"  # Wraps around

    def test_switch_proxy_skips_unhealthy(self):
        manager = ProxyManager(max_failures=1, cooldown_seconds=60)
        provider = GenericProvider(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        )
        manager.add_provider(provider)
        manager.set_proxy(provider="generic", count=3)

        # Mark p2 as unhealthy
        manager.record_failure("http://p2:8080", "Connection refused")
        manager.switch_proxy()

        # Should skip p2 and go to p3
        assert manager.get_current_proxy() == "http://p3:8080"

    def test_switch_proxy_no_healthy_raises(self):
        manager = ProxyManager(max_failures=1, cooldown_seconds=60)
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        manager.set_proxy(provider="generic")

        manager.record_failure("http://p1:8080", "Error")
        with pytest.raises(NoHealthyProxiesError):
            manager.switch_proxy()

    def test_record_success(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        manager.set_proxy(provider="generic")

        manager.record_success("http://p1:8080", 0.5)
        health = manager.get_health("http://p1:8080")
        assert health is not None
        assert health.total_requests == 1
        assert health.avg_response_time == 0.5

    def test_record_failure(self):
        manager = ProxyManager(max_failures=3)
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        manager.set_proxy(provider="generic")

        manager.record_failure("http://p1:8080", "Timeout")
        health = manager.get_health("http://p1:8080")
        assert health is not None
        assert health.consecutive_failures == 1

    def test_get_stats(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080", "http://p2:8080"])
        manager.add_provider(provider)
        manager.set_proxy(provider="generic", count=2)

        manager.record_success("http://p1:8080", 0.5)
        manager.record_success("http://p2:8080", 0.3)
        manager.record_failure("http://p1:8080", "Error")

        stats = manager.get_stats()
        assert stats.total_proxies == 2
        assert stats.healthy_proxies == 2
        assert stats.total_requests == 3
        assert stats.total_failures == 1


# ========== Async Tests ==========


class TestProxyManagerAsync:
    @pytest.mark.asyncio
    async def test_set_proxy_async(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        await manager.set_proxy_async(provider="generic")
        assert manager.has_proxy

    @pytest.mark.asyncio
    async def test_reset_proxy_async(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        await manager.set_proxy_async(provider="generic")
        await manager.reset_proxy_async()
        assert not manager.has_proxy

    @pytest.mark.asyncio
    async def test_switch_proxy_async(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080", "http://p2:8080"])
        manager.add_provider(provider)
        await manager.set_proxy_async(provider="generic", count=2)

        config = await manager.switch_proxy_async()
        assert config is not None
        assert config.url == "http://p2:8080"

    @pytest.mark.asyncio
    async def test_record_success_async(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        await manager.set_proxy_async(provider="generic")

        await manager.record_success_async("http://p1:8080", 0.5)
        health = manager.get_health("http://p1:8080")
        assert health.total_requests == 1

    @pytest.mark.asyncio
    async def test_record_failure_async(self):
        manager = ProxyManager()
        provider = GenericProvider(proxies=["http://p1:8080"])
        manager.add_provider(provider)
        await manager.set_proxy_async(provider="generic")

        await manager.record_failure_async("http://p1:8080", "Error")
        health = manager.get_health("http://p1:8080")
        assert health.consecutive_failures == 1


# ========== HTTPClient Integration Tests ==========


class TestHTTPClientProxyIntegration:
    def test_set_proxy_with_url(self):
        from http_client import HTTPClient

        client = HTTPClient()
        client.set_proxy(url="http://proxy:8080")
        assert client.get_current_proxy() == "http://proxy:8080"
        client.close()

    def test_set_proxy_backward_compat(self):
        from http_client import HTTPClient

        client = HTTPClient()
        client.set_proxy("http://proxy:8080")
        assert client.get_current_proxy() == "http://proxy:8080"
        client.close()

    def test_set_proxy_with_proxies_list(self):
        from http_client import HTTPClient

        client = HTTPClient()
        client.set_proxy(proxies=["http://p1:8080", "http://p2:8080"])
        assert client.get_current_proxy() == "http://p1:8080"
        client.close()

    def test_switch_proxy(self):
        from http_client import HTTPClient

        client = HTTPClient()
        client.set_proxy(proxies=["http://p1:8080", "http://p2:8080"])
        assert client.get_current_proxy() == "http://p1:8080"
        client.switch_proxy()
        assert client.get_current_proxy() == "http://p2:8080"
        client.close()

    def test_reset_proxy(self):
        from http_client import HTTPClient

        client = HTTPClient()
        client.set_proxy(proxies=["http://p1:8080"])
        assert client.get_current_proxy() == "http://p1:8080"
        client.reset_proxy()
        assert client.get_current_proxy() is None
        client.close()

    def test_set_proxy_none_clears(self):
        from http_client import HTTPClient

        client = HTTPClient()
        client.set_proxy("http://proxy:8080")
        assert client.get_current_proxy() == "http://proxy:8080"
        client.set_proxy(None)
        assert client.get_current_proxy() is None
        client.close()

    def test_add_proxy_provider(self):
        from http_client import HTTPClient

        client = HTTPClient()
        provider = GenericProvider(
            proxies=[
                {"url": "http://us1:8080", "country": "US"},
                {"url": "http://gb1:8080", "country": "GB"},
            ]
        )
        client.add_proxy_provider(provider)
        client.set_proxy(provider="generic", country="US")
        assert client.get_current_proxy() == "http://us1:8080"
        client.close()

    def test_proxy_manager_property(self):
        from http_client import HTTPClient

        client = HTTPClient()
        manager = client.proxy_manager
        assert isinstance(manager, ProxyManager)
        client.close()

    def test_proxy_manager_stats(self):
        from http_client import HTTPClient

        client = HTTPClient()
        client.set_proxy(proxies=["http://p1:8080", "http://p2:8080"])
        stats = client.proxy_manager.get_stats()
        assert stats.total_proxies == 2
        client.close()


# ========== HTTPClient Async Integration Tests ==========


class TestHTTPClientProxyIntegrationAsync:
    @pytest.mark.asyncio
    async def test_set_proxy_async_with_url(self):
        from http_client import HTTPClient

        client = HTTPClient()
        await client.set_proxy_async(url="http://proxy:8080")
        assert client.get_current_proxy() == "http://proxy:8080"
        await client.close_async()

    @pytest.mark.asyncio
    async def test_set_proxy_async_with_proxies_list(self):
        from http_client import HTTPClient

        client = HTTPClient()
        await client.set_proxy_async(proxies=["http://p1:8080", "http://p2:8080"])
        assert client.get_current_proxy() == "http://p1:8080"
        await client.close_async()

    @pytest.mark.asyncio
    async def test_switch_proxy_async(self):
        from http_client import HTTPClient

        client = HTTPClient()
        await client.set_proxy_async(proxies=["http://p1:8080", "http://p2:8080"])
        assert client.get_current_proxy() == "http://p1:8080"
        new_proxy = await client.switch_proxy_async()
        assert new_proxy == "http://p2:8080"
        assert client.get_current_proxy() == "http://p2:8080"
        await client.close_async()

    @pytest.mark.asyncio
    async def test_get_current_proxy_async(self):
        from http_client import HTTPClient

        client = HTTPClient()
        await client.set_proxy_async(proxies=["http://p1:8080"])
        proxy = await client.get_current_proxy_async()
        assert proxy == "http://p1:8080"
        await client.close_async()

    @pytest.mark.asyncio
    async def test_reset_proxy_async(self):
        from http_client import HTTPClient

        client = HTTPClient()
        await client.set_proxy_async(proxies=["http://p1:8080"])
        assert client.get_current_proxy() == "http://p1:8080"
        await client.reset_proxy_async()
        proxy = await client.get_current_proxy_async()
        assert proxy is None
        await client.close_async()


# ========== Exception Tests ==========


class TestProxyExceptions:
    def test_proxy_error_hierarchy(self):
        assert issubclass(ProxyConfigurationError, ProxyError)
        assert issubclass(NoHealthyProxiesError, ProxyError)
        assert issubclass(ProviderNotFoundError, ProxyError)

    def test_provider_not_found_error(self):
        error = ProviderNotFoundError("brightdata")
        assert error.provider_name == "brightdata"
        assert "brightdata" in str(error)

    def test_proxy_configuration_error(self):
        error = ProxyConfigurationError("Invalid config", config={"url": None})
        assert error.config == {"url": None}
