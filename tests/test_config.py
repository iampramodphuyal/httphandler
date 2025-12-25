"""Tests for ClientConfig."""

import pytest

from http_client import ClientConfig


class TestClientConfig:
    """Tests for ClientConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ClientConfig()

        assert config.mode == "speed"
        assert config.persist_cookies is False
        assert config.profile == "chrome_120"
        assert config.rate_limit == 2.0
        assert config.timeout == 30.0
        assert config.connect_timeout == 10.0
        assert config.retries == 3
        assert config.retry_codes == (429, 500, 502, 503, 504, 520, 521, 522, 523, 524)
        assert config.retry_backoff_base == 2.0
        assert config.proxies is None
        assert config.proxy_strategy == "round_robin"
        assert config.proxy_max_failures == 3
        assert config.proxy_cooldown == 300.0
        assert config.max_workers == 10
        assert config.default_concurrency == 10
        assert config.min_delay == 1.0
        assert config.max_delay == 3.0
        assert config.verify_ssl is True
        assert config.follow_redirects is True
        assert config.max_redirects == 10
        assert config.default_headers == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ClientConfig(
            mode="stealth",
            persist_cookies=True,
            profile="firefox_121",
            rate_limit=5.0,
            timeout=60.0,
            retries=5,
            proxies=["http://proxy:8080"],
            max_workers=20,
        )

        assert config.mode == "stealth"
        assert config.persist_cookies is True
        assert config.profile == "firefox_121"
        assert config.rate_limit == 5.0
        assert config.timeout == 60.0
        assert config.retries == 5
        assert config.proxies == ["http://proxy:8080"]
        assert config.max_workers == 20

    def test_validation_negative_rate_limit(self):
        """Test validation rejects negative rate limit."""
        with pytest.raises(ValueError, match="rate_limit must be >= 0"):
            ClientConfig(rate_limit=-1)

    def test_validation_zero_timeout(self):
        """Test validation rejects zero timeout."""
        with pytest.raises(ValueError, match="timeout must be > 0"):
            ClientConfig(timeout=0)

    def test_validation_negative_timeout(self):
        """Test validation rejects negative timeout."""
        with pytest.raises(ValueError, match="timeout must be > 0"):
            ClientConfig(timeout=-1)

    def test_validation_zero_connect_timeout(self):
        """Test validation rejects zero connect timeout."""
        with pytest.raises(ValueError, match="connect_timeout must be > 0"):
            ClientConfig(connect_timeout=0)

    def test_validation_negative_retries(self):
        """Test validation rejects negative retries."""
        with pytest.raises(ValueError, match="retries must be >= 0"):
            ClientConfig(retries=-1)

    def test_validation_zero_max_workers(self):
        """Test validation rejects zero max workers."""
        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            ClientConfig(max_workers=0)

    def test_validation_zero_concurrency(self):
        """Test validation rejects zero concurrency."""
        with pytest.raises(ValueError, match="default_concurrency must be >= 1"):
            ClientConfig(default_concurrency=0)

    def test_validation_negative_delays(self):
        """Test validation rejects negative delays."""
        with pytest.raises(ValueError, match="delays must be >= 0"):
            ClientConfig(min_delay=-1)

        with pytest.raises(ValueError, match="delays must be >= 0"):
            ClientConfig(max_delay=-1)

    def test_validation_min_delay_greater_than_max(self):
        """Test validation rejects min_delay > max_delay."""
        with pytest.raises(ValueError, match="min_delay must be <= max_delay"):
            ClientConfig(min_delay=5.0, max_delay=1.0)

    def test_zero_rate_limit_allowed(self):
        """Test that zero rate limit is allowed (disables rate limiting)."""
        config = ClientConfig(rate_limit=0)
        assert config.rate_limit == 0

    def test_zero_retries_allowed(self):
        """Test that zero retries is allowed (no retries)."""
        config = ClientConfig(retries=0)
        assert config.retries == 0

    def test_default_headers(self):
        """Test custom default headers."""
        headers = {"X-Custom": "value", "Authorization": "Bearer token"}
        config = ClientConfig(default_headers=headers)
        assert config.default_headers == headers

    def test_proxy_configuration(self):
        """Test proxy-related configuration."""
        config = ClientConfig(
            proxies=["http://p1:8080", "socks5://p2:1080"],
            proxy_strategy="random",
            proxy_max_failures=5,
            proxy_cooldown=600.0,
        )

        assert len(config.proxies) == 2
        assert config.proxy_strategy == "random"
        assert config.proxy_max_failures == 5
        assert config.proxy_cooldown == 600.0
