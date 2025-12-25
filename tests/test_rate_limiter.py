"""Tests for rate limiter."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from http_client.safety import TokenBucket, DomainRateLimiter


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    def test_initial_tokens(self):
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        assert bucket.available_tokens == 10.0

    def test_default_capacity(self):
        """Test default capacity equals rate."""
        bucket = TokenBucket(rate=5.0)
        assert bucket.available_tokens == 5.0

    def test_acquire_sync_immediate(self):
        """Test immediate token acquisition."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        # Should acquire immediately
        start = time.monotonic()
        result = bucket.acquire_sync()
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed < 0.1  # Should be nearly instant
        assert bucket.available_tokens < 10.0

    def test_acquire_sync_multiple(self):
        """Test multiple token acquisitions."""
        bucket = TokenBucket(rate=10.0, capacity=5.0)

        # Acquire all tokens
        for _ in range(5):
            assert bucket.acquire_sync() is True

        # Next one should block briefly
        start = time.monotonic()
        assert bucket.acquire_sync() is True
        elapsed = time.monotonic() - start

        assert elapsed >= 0.09  # Should wait for at least one token

    def test_acquire_sync_non_blocking(self):
        """Test non-blocking token acquisition."""
        bucket = TokenBucket(rate=1.0, capacity=1.0)

        # First should succeed
        assert bucket.acquire_sync(blocking=False) is True

        # Second should fail immediately (no waiting)
        start = time.monotonic()
        result = bucket.acquire_sync(blocking=False)
        elapsed = time.monotonic() - start

        assert result is False
        assert elapsed < 0.1  # Should return immediately

    def test_token_refill(self):
        """Test tokens refill over time."""
        bucket = TokenBucket(rate=10.0, capacity=5.0)

        # Use all tokens
        for _ in range(5):
            bucket.acquire_sync()

        # Wait for refill
        time.sleep(0.3)

        # Should have ~3 tokens now
        tokens = bucket.available_tokens
        assert 2.5 <= tokens <= 3.5

    @pytest.mark.asyncio
    async def test_acquire_async_immediate(self):
        """Test immediate async token acquisition."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        start = time.monotonic()
        result = await bucket.acquire_async()
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_acquire_async_non_blocking(self):
        """Test non-blocking async token acquisition."""
        bucket = TokenBucket(rate=1.0, capacity=1.0)

        # First should succeed
        assert await bucket.acquire_async(blocking=False) is True

        # Second should fail immediately
        result = await bucket.acquire_async(blocking=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_acquire_async_concurrent(self):
        """Test concurrent async acquisitions."""
        bucket = TokenBucket(rate=10.0, capacity=3.0)

        async def acquire_one():
            return await bucket.acquire_async()

        # Run multiple acquisitions concurrently
        results = await asyncio.gather(*[acquire_one() for _ in range(5)])

        assert all(results)  # All should eventually succeed

    def test_thread_safety(self):
        """Test thread-safe token acquisition."""
        bucket = TokenBucket(rate=100.0, capacity=10.0)
        results = []

        def acquire_tokens(n):
            local_results = []
            for _ in range(n):
                local_results.append(bucket.acquire_sync())
            results.extend(local_results)

        # Run multiple threads
        threads = [
            threading.Thread(target=acquire_tokens, args=(10,))
            for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed (with blocking)
        assert len(results) == 50
        assert all(results)


class TestDomainRateLimiter:
    """Tests for DomainRateLimiter."""

    def test_default_rate(self):
        """Test default rate is applied to all domains."""
        limiter = DomainRateLimiter(default_rate=10.0)

        info = limiter.get_domain_info("https://example.com/path")
        assert info["rate"] == 10.0
        assert info["rate_limiting_enabled"] is True

    def test_rate_limiting_disabled(self):
        """Test rate limiting can be disabled."""
        limiter = DomainRateLimiter(default_rate=0)

        info = limiter.get_domain_info("https://example.com/path")
        assert info["rate"] == 0
        assert info["rate_limiting_enabled"] is False

    def test_domain_extraction(self):
        """Test domain is correctly extracted from URL."""
        limiter = DomainRateLimiter(default_rate=5.0)

        info1 = limiter.get_domain_info("https://example.com/path")
        info2 = limiter.get_domain_info("https://example.com/other")
        info3 = limiter.get_domain_info("https://other.com/path")

        assert info1["domain"] == "example.com"
        assert info2["domain"] == "example.com"
        assert info3["domain"] == "other.com"

    def test_per_domain_rates(self):
        """Test custom rates per domain."""
        limiter = DomainRateLimiter(
            default_rate=2.0,
            domain_rates={"api.example.com": 10.0, "slow.example.com": 0.5},
        )

        assert limiter.get_domain_info("https://example.com")["rate"] == 2.0
        assert limiter.get_domain_info("https://api.example.com")["rate"] == 10.0
        assert limiter.get_domain_info("https://slow.example.com")["rate"] == 0.5

    def test_set_domain_rate(self):
        """Test setting domain rate dynamically."""
        limiter = DomainRateLimiter(default_rate=2.0)

        limiter.set_domain_rate("example.com", 20.0)

        assert limiter.get_domain_info("https://example.com")["rate"] == 20.0

    def test_acquire_sync(self):
        """Test synchronous rate limit acquisition."""
        limiter = DomainRateLimiter(default_rate=100.0)

        # Should acquire immediately with high rate
        start = time.monotonic()
        result = limiter.acquire_sync("https://example.com")
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed < 0.1

    def test_acquire_sync_disabled(self):
        """Test acquisition when rate limiting is disabled."""
        limiter = DomainRateLimiter(default_rate=0)

        # Should always succeed immediately
        for _ in range(100):
            assert limiter.acquire_sync("https://example.com") is True

    @pytest.mark.asyncio
    async def test_acquire_async(self):
        """Test async rate limit acquisition."""
        limiter = DomainRateLimiter(default_rate=100.0)

        result = await limiter.acquire_async("https://example.com")
        assert result is True

    def test_separate_buckets_per_domain(self):
        """Test each domain has separate bucket."""
        limiter = DomainRateLimiter(default_rate=2.0)

        # Acquire from domain 1 (exhausts tokens)
        limiter.acquire_sync("https://domain1.com")
        limiter.acquire_sync("https://domain1.com")

        # Domain 1 should have used tokens
        info1 = limiter.get_domain_info("https://domain1.com")
        assert info1["tokens"] < 2.0  # Tokens consumed

        # Acquire from domain 2 - should have fresh tokens
        limiter.acquire_sync("https://domain2.com")
        info2 = limiter.get_domain_info("https://domain2.com")
        # After one acquire, should have ~1 token left
        assert info2["tokens"] < 2.0
        assert info2["tokens"] > 0.5  # But more than domain1 had

    def test_global_rate_limit(self):
        """Test global rate limit across all domains."""
        limiter = DomainRateLimiter(default_rate=10.0, global_rate=5.0)

        # Make requests to different domains
        start = time.monotonic()
        for i in range(6):
            limiter.acquire_sync(f"https://domain{i}.com")
        elapsed = time.monotonic() - start

        # Should be rate limited globally
        assert elapsed >= 0.1  # At least one global wait

    def test_thread_pool_safety(self):
        """Test rate limiter is safe with thread pool."""
        limiter = DomainRateLimiter(default_rate=100.0)
        results = []

        def acquire(url):
            return limiter.acquire_sync(url)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(acquire, f"https://example.com/{i}")
                for i in range(50)
            ]
            results = [f.result() for f in futures]

        assert all(results)
