"""Tests for proxy pool."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from http_client.safety import Proxy, ProxyPool


class TestProxy:
    """Tests for Proxy dataclass."""

    def test_basic_proxy(self):
        """Test basic proxy creation."""
        proxy = Proxy(url="http://proxy.example.com:8080")

        assert proxy.url == "http://proxy.example.com:8080"
        assert proxy.enabled is True
        assert proxy.consecutive_failures == 0
        assert proxy.total_requests == 0
        assert proxy.total_failures == 0

    def test_proxy_protocol(self):
        """Test protocol extraction."""
        http_proxy = Proxy(url="http://proxy:8080")
        socks_proxy = Proxy(url="socks5://proxy:1080")
        https_proxy = Proxy(url="https://proxy:443")

        assert http_proxy.protocol == "http"
        assert socks_proxy.protocol == "socks5"
        assert https_proxy.protocol == "https"

    def test_proxy_host_port(self):
        """Test host and port extraction."""
        proxy = Proxy(url="http://proxy.example.com:8080")

        assert proxy.host == "proxy.example.com"
        assert proxy.port == 8080

    def test_proxy_with_auth(self):
        """Test proxy with authentication."""
        proxy = Proxy(url="http://user:pass@proxy.example.com:8080")

        assert proxy.host == "proxy.example.com"
        assert proxy.port == 8080

    def test_success_rate(self):
        """Test success rate calculation."""
        proxy = Proxy(url="http://proxy:8080")

        # No requests yet
        assert proxy.success_rate == 1.0

        # Simulate requests
        proxy.total_requests = 10
        proxy.total_failures = 3
        assert proxy.success_rate == 0.7

        proxy.total_requests = 10
        proxy.total_failures = 10
        assert proxy.success_rate == 0.0

    def test_reset_stats(self):
        """Test resetting proxy statistics."""
        proxy = Proxy(
            url="http://proxy:8080",
            consecutive_failures=5,
            total_requests=100,
            total_failures=20,
            last_used=time.monotonic(),
        )

        proxy.reset_stats()

        assert proxy.consecutive_failures == 0
        assert proxy.total_requests == 0
        assert proxy.total_failures == 0
        assert proxy.last_used == 0.0


class TestProxyPool:
    """Tests for ProxyPool."""

    def test_empty_pool(self):
        """Test empty proxy pool."""
        pool = ProxyPool()

        assert pool.total_count == 0
        assert pool.available_count == 0
        assert pool.get_proxy() is None
        assert not pool.has_proxies
        assert len(pool) == 0
        assert not pool

    def test_pool_with_proxies(self):
        """Test pool with initial proxies."""
        pool = ProxyPool(proxies=["http://p1:8080", "http://p2:8080"])

        assert pool.total_count == 2
        assert pool.available_count == 2
        assert pool.has_proxies
        assert len(pool) == 2
        assert pool

    def test_add_proxy(self):
        """Test adding proxy to pool."""
        pool = ProxyPool()
        pool.add_proxy("http://proxy:8080")

        assert pool.total_count == 1
        assert pool.get_proxy().url == "http://proxy:8080"

    def test_add_duplicate_proxy(self):
        """Test adding duplicate proxy."""
        pool = ProxyPool(proxies=["http://proxy:8080"])
        pool.add_proxy("http://proxy:8080")

        assert pool.total_count == 1  # Should not add duplicate

    def test_remove_proxy(self):
        """Test removing proxy from pool."""
        pool = ProxyPool(proxies=["http://p1:8080", "http://p2:8080"])

        result = pool.remove_proxy("http://p1:8080")
        assert result is True
        assert pool.total_count == 1

        result = pool.remove_proxy("http://nonexistent:8080")
        assert result is False

    def test_round_robin_strategy(self):
        """Test round-robin proxy selection."""
        pool = ProxyPool(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"],
            strategy="round_robin",
        )

        # Should cycle through proxies
        urls = [pool.get_proxy().url for _ in range(6)]

        assert urls == [
            "http://p1:8080",
            "http://p2:8080",
            "http://p3:8080",
            "http://p1:8080",
            "http://p2:8080",
            "http://p3:8080",
        ]

    def test_random_strategy(self):
        """Test random proxy selection."""
        pool = ProxyPool(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"],
            strategy="random",
        )

        # Get multiple proxies
        urls = [pool.get_proxy().url for _ in range(30)]

        # All should be valid
        valid_urls = {"http://p1:8080", "http://p2:8080", "http://p3:8080"}
        assert all(url in valid_urls for url in urls)

        # Should have some variety (probabilistic but very likely)
        assert len(set(urls)) > 1

    def test_least_used_strategy(self):
        """Test least-recently-used proxy selection."""
        pool = ProxyPool(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"],
            strategy="least_used",
        )

        # First call should get any (all have same last_used=0)
        proxy1 = pool.get_proxy()
        time.sleep(0.01)

        # Second should get a different one
        proxy2 = pool.get_proxy()
        time.sleep(0.01)

        # Third should get the remaining one
        proxy3 = pool.get_proxy()

        # Should have gotten all three different proxies
        urls = {proxy1.url, proxy2.url, proxy3.url}
        assert len(urls) == 3

    def test_report_success(self):
        """Test reporting successful request."""
        pool = ProxyPool(proxies=["http://proxy:8080"], max_failures=3)

        proxy = pool.get_proxy()
        proxy.consecutive_failures = 2

        pool.report_success(proxy.url)

        assert proxy.consecutive_failures == 0

    def test_report_failure(self):
        """Test reporting failed request."""
        pool = ProxyPool(proxies=["http://proxy:8080"], max_failures=3)

        proxy = pool.get_proxy()
        pool.report_failure(proxy.url)

        assert proxy.consecutive_failures == 1
        assert proxy.total_failures == 1
        assert proxy.enabled is True  # Not disabled yet

    def test_auto_disable_on_failures(self):
        """Test proxy is disabled after max failures."""
        pool = ProxyPool(proxies=["http://proxy:8080"], max_failures=3)

        proxy = pool.get_proxy()

        # Report max failures
        for _ in range(3):
            pool.report_failure(proxy.url)

        assert proxy.enabled is False
        assert pool.available_count == 0

    def test_auto_recovery(self):
        """Test proxy is re-enabled after cooldown."""
        pool = ProxyPool(
            proxies=["http://proxy:8080"],
            max_failures=2,
            cooldown=0.1,  # Very short for testing
        )

        proxy = pool.get_proxy()

        # Disable proxy
        for _ in range(2):
            pool.report_failure(proxy.url)

        assert proxy.enabled is False
        assert pool.available_count == 0

        # Wait for cooldown
        time.sleep(0.15)

        # Should be re-enabled on next get
        recovered = pool.get_proxy()
        assert recovered is not None
        assert recovered.enabled is True
        assert recovered.consecutive_failures == 0

    def test_force_disable(self):
        """Test forcefully disabling a proxy."""
        pool = ProxyPool(proxies=["http://p1:8080", "http://p2:8080"])

        pool.force_disable("http://p1:8080")

        assert pool.available_count == 1
        assert pool.get_proxy().url == "http://p2:8080"

    def test_force_enable(self):
        """Test forcefully enabling a proxy."""
        pool = ProxyPool(proxies=["http://proxy:8080"], max_failures=1)

        proxy = pool.get_proxy()
        pool.report_failure(proxy.url)
        assert pool.available_count == 0

        pool.force_enable("http://proxy:8080")
        assert pool.available_count == 1

    def test_reset_all(self):
        """Test resetting all proxies."""
        pool = ProxyPool(proxies=["http://p1:8080", "http://p2:8080"], max_failures=1)

        # Disable all proxies
        pool.report_failure("http://p1:8080")
        pool.report_failure("http://p2:8080")
        assert pool.available_count == 0

        pool.reset_all()

        assert pool.available_count == 2

    def test_get_stats(self):
        """Test getting pool statistics."""
        pool = ProxyPool(
            proxies=["http://p1:8080", "http://p2:8080"],
            max_failures=2,
        )

        # Use and fail one proxy
        pool.get_proxy()
        pool.report_failure("http://p1:8080")
        pool.report_failure("http://p1:8080")

        stats = pool.get_stats()

        assert stats["total"] == 2
        assert stats["available"] == 1
        assert stats["disabled"] == 1
        assert stats["strategy"] == "round_robin"
        assert len(stats["proxies"]) == 2

    def test_thread_safety(self):
        """Test thread-safe proxy pool operations."""
        pool = ProxyPool(
            proxies=["http://p1:8080", "http://p2:8080", "http://p3:8080"],
            strategy="round_robin",
            max_failures=100,  # High to avoid disabling
        )

        results = []

        def use_proxy():
            for _ in range(10):
                proxy = pool.get_proxy()
                if proxy:
                    results.append(proxy.url)
                    pool.report_success(proxy.url)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(use_proxy) for _ in range(5)]
            for f in futures:
                f.result()

        assert len(results) == 50  # All operations completed
