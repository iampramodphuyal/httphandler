"""Tests for cookie store."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from http_client.safety import CookieStore
from http_client.safety.cookie_store import Cookie


class TestCookie:
    """Tests for Cookie dataclass."""

    def test_basic_cookie(self):
        """Test basic cookie creation."""
        cookie = Cookie(name="session", value="abc123", domain="example.com")

        assert cookie.name == "session"
        assert cookie.value == "abc123"
        assert cookie.domain == "example.com"
        assert cookie.path == "/"
        assert cookie.expires is None
        assert cookie.secure is False
        assert cookie.http_only is False

    def test_cookie_not_expired(self):
        """Test cookie expiration check for non-expired cookie."""
        cookie = Cookie(
            name="session",
            value="abc",
            domain="example.com",
            expires=time.time() + 3600,  # 1 hour from now
        )

        assert cookie.is_expired is False

    def test_cookie_expired(self):
        """Test cookie expiration check for expired cookie."""
        cookie = Cookie(
            name="session",
            value="abc",
            domain="example.com",
            expires=time.time() - 3600,  # 1 hour ago
        )

        assert cookie.is_expired is True

    def test_session_cookie_never_expires(self):
        """Test session cookie (no expires) never expires."""
        cookie = Cookie(name="session", value="abc", domain="example.com")
        assert cookie.is_expired is False

    def test_matches_domain_exact(self):
        """Test exact domain matching."""
        cookie = Cookie(name="session", value="abc", domain="example.com")

        assert cookie.matches_domain("example.com") is True
        assert cookie.matches_domain("EXAMPLE.COM") is True  # Case insensitive
        assert cookie.matches_domain("other.com") is False

    def test_matches_domain_with_dot(self):
        """Test domain matching with leading dot."""
        cookie = Cookie(name="session", value="abc", domain=".example.com")

        assert cookie.matches_domain("example.com") is True
        assert cookie.matches_domain("www.example.com") is True
        assert cookie.matches_domain("api.example.com") is True
        assert cookie.matches_domain("other.com") is False

    def test_matches_path(self):
        """Test path matching."""
        cookie = Cookie(name="session", value="abc", domain="example.com", path="/api")

        assert cookie.matches_path("/api") is True
        assert cookie.matches_path("/api/users") is True
        assert cookie.matches_path("/other") is False

    def test_matches_path_root(self):
        """Test root path matches everything."""
        cookie = Cookie(name="session", value="abc", domain="example.com", path="/")

        assert cookie.matches_path("/") is True
        assert cookie.matches_path("/any/path") is True


class TestCookieStore:
    """Tests for CookieStore."""

    def test_empty_store(self):
        """Test empty cookie store."""
        store = CookieStore()

        assert len(store) == 0
        assert not store
        assert store.get_all() == {}

    def test_set_cookie(self):
        """Test setting a cookie."""
        store = CookieStore()
        store.set("session", "abc123", domain="example.com")

        assert len(store) == 1
        assert store

    def test_get_cookies_for_url(self):
        """Test getting cookies for URL."""
        store = CookieStore()
        store.set("session", "abc123", domain="example.com")
        store.set("other", "xyz", domain="other.com")

        cookies = store.get_for_url("https://example.com/path")

        assert cookies == {"session": "abc123"}

    def test_get_cookies_path_matching(self):
        """Test cookie path matching."""
        store = CookieStore()
        store.set("root_cookie", "1", domain="example.com", path="/")
        store.set("api_cookie", "2", domain="example.com", path="/api")

        # Root path should get only root cookie
        root_cookies = store.get_for_url("https://example.com/other")
        assert root_cookies == {"root_cookie": "1"}

        # API path should get both
        api_cookies = store.get_for_url("https://example.com/api/users")
        assert api_cookies == {"root_cookie": "1", "api_cookie": "2"}

    def test_secure_cookie_https_only(self):
        """Test secure cookies only sent over HTTPS."""
        store = CookieStore()
        store.set("secure_cookie", "secret", domain="example.com", secure=True)
        store.set("normal_cookie", "normal", domain="example.com", secure=False)

        # HTTPS should get both
        https_cookies = store.get_for_url("https://example.com")
        assert "secure_cookie" in https_cookies
        assert "normal_cookie" in https_cookies

        # HTTP should only get non-secure
        http_cookies = store.get_for_url("http://example.com")
        assert "secure_cookie" not in http_cookies
        assert "normal_cookie" in http_cookies

    def test_expired_cookies_not_returned(self):
        """Test expired cookies are not returned."""
        store = CookieStore()
        store.set(
            "expired",
            "old",
            domain="example.com",
            expires=time.time() - 3600,
        )
        store.set("valid", "new", domain="example.com")

        cookies = store.get_for_url("https://example.com")

        assert "expired" not in cookies
        assert "valid" in cookies

    def test_update_from_response(self):
        """Test updating cookies from response."""
        store = CookieStore()
        store.update_from_response(
            "https://example.com/login",
            {"session": "abc", "user": "test"},
        )

        cookies = store.get_for_url("https://example.com")
        assert cookies == {"session": "abc", "user": "test"}

    def test_delete_cookie(self):
        """Test deleting a specific cookie."""
        store = CookieStore()
        store.set("cookie1", "1", domain="example.com")
        store.set("cookie2", "2", domain="example.com")

        result = store.delete("cookie1", "example.com")
        assert result is True
        assert len(store) == 1

        # Try to delete non-existent
        result = store.delete("nonexistent", "example.com")
        assert result is False

    def test_clear_domain(self):
        """Test clearing cookies for a domain."""
        store = CookieStore()
        store.set("c1", "1", domain="example.com")
        store.set("c2", "2", domain="example.com")
        store.set("c3", "3", domain="other.com")

        store.clear_domain("example.com")

        assert len(store) == 1
        assert store.get_for_url("https://example.com") == {}
        assert store.get_for_url("https://other.com") == {"c3": "3"}

    def test_clear_all(self):
        """Test clearing all cookies."""
        store = CookieStore()
        store.set("c1", "1", domain="example.com")
        store.set("c2", "2", domain="other.com")

        store.clear_all()

        assert len(store) == 0
        assert store.get_all() == {}

    def test_get_all(self):
        """Test getting all cookies."""
        store = CookieStore()
        store.set("c1", "1", domain="example.com")
        store.set("c2", "2", domain="example.com")
        store.set("c3", "3", domain="other.com")

        all_cookies = store.get_all()

        assert all_cookies == {
            "example.com": {"c1": "1", "c2": "2"},
            "other.com": {"c3": "3"},
        }

    def test_cookie_overwrite(self):
        """Test overwriting existing cookie."""
        store = CookieStore()
        store.set("session", "old_value", domain="example.com")
        store.set("session", "new_value", domain="example.com")

        cookies = store.get_for_url("https://example.com")
        assert cookies == {"session": "new_value"}
        assert len(store) == 1

    @pytest.mark.asyncio
    async def test_async_set(self):
        """Test async cookie setting."""
        store = CookieStore()
        await store.set_async("session", "abc", domain="example.com")

        cookies = store.get_for_url("https://example.com")
        assert cookies == {"session": "abc"}

    @pytest.mark.asyncio
    async def test_async_get_for_url(self):
        """Test async cookie retrieval."""
        store = CookieStore()
        store.set("session", "abc", domain="example.com")

        cookies = await store.get_for_url_async("https://example.com")
        assert cookies == {"session": "abc"}

    @pytest.mark.asyncio
    async def test_async_update_from_response(self):
        """Test async update from response."""
        store = CookieStore()
        await store.update_from_response_async(
            "https://example.com",
            {"session": "abc"},
        )

        cookies = await store.get_for_url_async("https://example.com")
        assert cookies == {"session": "abc"}

    def test_thread_safety(self):
        """Test thread-safe cookie operations."""
        store = CookieStore()
        errors = []

        def set_cookies(prefix):
            try:
                for i in range(50):
                    store.set(f"{prefix}_{i}", str(i), domain="example.com")
            except Exception as e:
                errors.append(e)

        def get_cookies():
            try:
                for _ in range(100):
                    store.get_for_url("https://example.com")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=set_cookies, args=("a",)),
            threading.Thread(target=set_cookies, args=("b",)),
            threading.Thread(target=get_cookies),
            threading.Thread(target=get_cookies),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(store) == 100  # 50 + 50 cookies

    @pytest.mark.asyncio
    async def test_async_concurrent_access(self):
        """Test concurrent async access."""
        store = CookieStore()

        async def set_cookies(prefix):
            for i in range(20):
                await store.set_async(f"{prefix}_{i}", str(i), domain="example.com")

        async def get_cookies():
            for _ in range(50):
                await store.get_for_url_async("https://example.com")

        await asyncio.gather(
            set_cookies("a"),
            set_cookies("b"),
            get_cookies(),
            get_cookies(),
        )

        assert len(store) == 40
