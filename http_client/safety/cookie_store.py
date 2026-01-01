"""Thread-safe and async-safe cookie storage."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from http.cookies import SimpleCookie
from typing import Iterator
from urllib.parse import urlparse


@dataclass
class Cookie:
    """Cookie representation.

    Attributes:
        name: Cookie name.
        value: Cookie value.
        domain: Cookie domain.
        path: Cookie path.
        expires: Expiration timestamp (None for session cookie).
        secure: Whether cookie requires HTTPS.
        http_only: Whether cookie is HTTP-only.
    """

    name: str
    value: str
    domain: str = ""
    path: str = "/"
    expires: float | None = None
    secure: bool = False
    http_only: bool = False

    @property
    def is_expired(self) -> bool:
        """Check if cookie has expired."""
        if self.expires is None:
            return False
        return time.time() > self.expires

    def matches_domain(self, domain: str) -> bool:
        """Check if cookie matches the given domain."""
        domain = domain.lower()
        cookie_domain = self.domain.lower()

        # Exact match
        if domain == cookie_domain:
            return True

        # Domain attribute match (cookie domain starts with dot)
        if cookie_domain.startswith("."):
            return domain.endswith(cookie_domain) or domain == cookie_domain[1:]

        # Subdomain match
        return domain.endswith("." + cookie_domain)

    def matches_path(self, path: str) -> bool:
        """Check if cookie matches the given path."""
        if self.path == "/":
            return True
        return path.startswith(self.path)


class CookieStore:
    """Thread-safe and async-safe cookie storage with per-domain organization.

    Uses dual-lock pattern:
    - threading.Lock for thread safety
    - asyncio.Lock for async task safety (lazy initialized)
    """

    def __init__(self):
        """Initialize empty cookie store."""
        # Domain -> {cookie_name: Cookie}
        self._cookies: dict[str, dict[str, Cookie]] = {}
        self._thread_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazily initialize async lock within event loop context.

        Creates lock on first async access. Thread-safe via _thread_lock.

        Returns:
            asyncio.Lock for async coordination.

        Raises:
            RuntimeError: If called outside an async context (no event loop).
        """
        # Use thread lock to safely check and create the async lock
        with self._thread_lock:
            if self._async_lock is None:
                try:
                    self._async_lock = asyncio.Lock()
                except RuntimeError as e:
                    raise RuntimeError(
                        "Cannot create asyncio.Lock outside of async context. "
                        "Use synchronous methods for non-async access."
                    ) from e
            return self._async_lock

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain for storage key."""
        domain = domain.lower()
        if domain.startswith("."):
            domain = domain[1:]
        return domain

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def _cleanup_expired(self) -> None:
        """Remove expired cookies. Must be called under lock."""
        for domain in list(self._cookies.keys()):
            domain_cookies = self._cookies[domain]
            expired = [name for name, cookie in domain_cookies.items() if cookie.is_expired]
            for name in expired:
                del domain_cookies[name]
            if not domain_cookies:
                del self._cookies[domain]

    def set(
        self,
        name: str,
        value: str,
        domain: str,
        path: str = "/",
        expires: float | None = None,
        secure: bool = False,
        http_only: bool = False,
    ) -> None:
        """Set a cookie (thread-safe).

        Args:
            name: Cookie name.
            value: Cookie value.
            domain: Cookie domain.
            path: Cookie path.
            expires: Expiration timestamp.
            secure: HTTPS-only flag.
            http_only: HTTP-only flag.
        """
        cookie = Cookie(
            name=name,
            value=value,
            domain=domain,
            path=path,
            expires=expires,
            secure=secure,
            http_only=http_only,
        )

        domain_key = self._normalize_domain(domain)

        with self._thread_lock:
            if domain_key not in self._cookies:
                self._cookies[domain_key] = {}
            self._cookies[domain_key][name] = cookie

    async def set_async(
        self,
        name: str,
        value: str,
        domain: str,
        path: str = "/",
        expires: float | None = None,
        secure: bool = False,
        http_only: bool = False,
    ) -> None:
        """Set a cookie (async-safe).

        Args:
            name: Cookie name.
            value: Cookie value.
            domain: Cookie domain.
            path: Cookie path.
            expires: Expiration timestamp.
            secure: HTTPS-only flag.
            http_only: HTTP-only flag.
        """
        cookie = Cookie(
            name=name,
            value=value,
            domain=domain,
            path=path,
            expires=expires,
            secure=secure,
            http_only=http_only,
        )

        domain_key = self._normalize_domain(domain)
        async_lock = self._get_async_lock()

        async with async_lock:
            with self._thread_lock:
                if domain_key not in self._cookies:
                    self._cookies[domain_key] = {}
                self._cookies[domain_key][name] = cookie

    def get_for_url(self, url: str) -> dict[str, str]:
        """Get cookies applicable to URL (thread-safe).

        Args:
            url: The request URL.

        Returns:
            Dict of cookie name to value.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path or "/"
        is_secure = parsed.scheme.lower() == "https"

        result: dict[str, str] = {}

        with self._thread_lock:
            self._cleanup_expired()

            for domain_key, domain_cookies in self._cookies.items():
                for name, cookie in domain_cookies.items():
                    if cookie.is_expired:
                        continue
                    if not cookie.matches_domain(domain):
                        continue
                    if not cookie.matches_path(path):
                        continue
                    if cookie.secure and not is_secure:
                        continue
                    result[name] = cookie.value

        return result

    async def get_for_url_async(self, url: str) -> dict[str, str]:
        """Get cookies applicable to URL (async-safe).

        Args:
            url: The request URL.

        Returns:
            Dict of cookie name to value.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path or "/"
        is_secure = parsed.scheme.lower() == "https"

        result: dict[str, str] = {}
        async_lock = self._get_async_lock()

        async with async_lock:
            with self._thread_lock:
                self._cleanup_expired()

                for domain_key, domain_cookies in self._cookies.items():
                    for name, cookie in domain_cookies.items():
                        if cookie.is_expired:
                            continue
                        if not cookie.matches_domain(domain):
                            continue
                        if not cookie.matches_path(path):
                            continue
                        if cookie.secure and not is_secure:
                            continue
                        result[name] = cookie.value

        return result

    def update_from_response(
        self,
        url: str,
        response_cookies: dict[str, str],
    ) -> None:
        """Update cookies from response (thread-safe).

        Args:
            url: The request URL (for domain inference).
            response_cookies: Dict of cookie name to value from response.
        """
        domain = self._get_domain_from_url(url)

        with self._thread_lock:
            if domain not in self._cookies:
                self._cookies[domain] = {}

            for name, value in response_cookies.items():
                self._cookies[domain][name] = Cookie(
                    name=name,
                    value=value,
                    domain=domain,
                )

    async def update_from_response_async(
        self,
        url: str,
        response_cookies: dict[str, str],
    ) -> None:
        """Update cookies from response (async-safe).

        Args:
            url: The request URL (for domain inference).
            response_cookies: Dict of cookie name to value from response.
        """
        domain = self._get_domain_from_url(url)
        async_lock = self._get_async_lock()

        async with async_lock:
            with self._thread_lock:
                if domain not in self._cookies:
                    self._cookies[domain] = {}

                for name, value in response_cookies.items():
                    self._cookies[domain][name] = Cookie(
                        name=name,
                        value=value,
                        domain=domain,
                    )

    def delete(self, name: str, domain: str) -> bool:
        """Delete a specific cookie.

        Args:
            name: Cookie name.
            domain: Cookie domain.

        Returns:
            True if cookie was deleted, False if not found.
        """
        domain_key = self._normalize_domain(domain)

        with self._thread_lock:
            if domain_key in self._cookies and name in self._cookies[domain_key]:
                del self._cookies[domain_key][name]
                if not self._cookies[domain_key]:
                    del self._cookies[domain_key]
                return True
            return False

    def clear_domain(self, domain: str) -> None:
        """Clear all cookies for a domain.

        Args:
            domain: Domain to clear.
        """
        domain_key = self._normalize_domain(domain)

        with self._thread_lock:
            self._cookies.pop(domain_key, None)

    def clear_all(self) -> None:
        """Clear all cookies."""
        with self._thread_lock:
            self._cookies.clear()

    def get_all(self) -> dict[str, dict[str, str]]:
        """Get all cookies organized by domain.

        Returns:
            Dict mapping domain to dict of cookie name/value pairs.
        """
        with self._thread_lock:
            self._cleanup_expired()
            return {
                domain: {name: cookie.value for name, cookie in cookies.items()}
                for domain, cookies in self._cookies.items()
            }

    def __len__(self) -> int:
        """Return total number of cookies."""
        with self._thread_lock:
            return sum(len(cookies) for cookies in self._cookies.values())

    def __bool__(self) -> bool:
        """Return True if store has any cookies."""
        with self._thread_lock:
            return any(self._cookies.values())
