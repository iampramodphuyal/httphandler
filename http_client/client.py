"""Unified HTTP client with per-request backend switching."""

from __future__ import annotations

from typing import Any, Literal

from .models import Response
from ._cookies import CookieStore
from ._backends import HttpxBackend, CurlBackend, CURL_AVAILABLE


class HTTPClient:
    """Unified HTTP client supporting httpx and curl_cffi backends.

    Features:
    - httpx as default backend (reliable, well-maintained)
    - Per-request backend switching for stealth needs
    - Shared cookie persistence across backends
    - Optional browser fingerprinting with curl_cffi

    Examples:
        # Simple usage (httpx backend)
        client = HTTPClient()
        response = client.get("https://api.example.com/data")

        # With cookie persistence
        client = HTTPClient(persist_cookies=True)
        client.post("https://example.com/login", json={"user": "..."})
        client.get("https://example.com/dashboard")  # Cookies sent

        # Per-request stealth mode
        response = client.get(
            "https://protected-site.com",
            backend="curl",
            stealth=True,
        )

        # Async usage
        async with HTTPClient() as client:
            response = await client.get_async("https://example.com")
    """

    def __init__(
        self,
        default_backend: Literal["httpx", "curl"] = "httpx",
        persist_cookies: bool = False,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        verify_ssl: bool = True,
        proxy: str | None = None,
        follow_redirects: bool = True,
        profile: str = "chrome_120",
    ):
        """Initialize HTTPClient.

        Args:
            default_backend: Default backend for requests ("httpx" or "curl").
            persist_cookies: Whether to persist cookies across requests.
            timeout: Default request timeout in seconds.
            headers: Default headers for all requests.
            verify_ssl: Whether to verify SSL certificates.
            proxy: Default proxy URL.
            follow_redirects: Whether to follow redirects.
            profile: Browser profile for curl stealth mode.
        """
        self._default_backend = default_backend
        self._timeout = timeout
        self._default_headers = dict(headers) if headers else {}
        self._verify_ssl = verify_ssl
        self._proxy = proxy
        self._follow_redirects = follow_redirects
        self._profile = profile

        # Cookie store (shared across backends)
        self._cookie_store: CookieStore | None = None
        if persist_cookies:
            self._cookie_store = CookieStore()

        # Lazy-initialized backends
        self._httpx_backend: HttpxBackend | None = None
        self._curl_backend: CurlBackend | None = None

        # State tracking
        self._last_response: Response | None = None
        self._closed = False

    def _get_httpx_backend(self) -> HttpxBackend:
        """Get or create httpx backend."""
        if self._httpx_backend is None:
            self._httpx_backend = HttpxBackend(
                timeout=self._timeout,
                verify_ssl=self._verify_ssl,
                follow_redirects=self._follow_redirects,
            )
        return self._httpx_backend

    def _get_curl_backend(self) -> CurlBackend:
        """Get or create curl backend."""
        if self._curl_backend is None:
            if not CURL_AVAILABLE:
                raise ImportError(
                    "curl_cffi is required for curl backend. "
                    "Install with: pip install curl_cffi"
                )
            self._curl_backend = CurlBackend(
                profile=self._profile,
                timeout=self._timeout,
                verify_ssl=self._verify_ssl,
                follow_redirects=self._follow_redirects,
            )
        return self._curl_backend

    def _resolve_backend(self, backend: str | None) -> str:
        """Resolve which backend to use."""
        return backend or self._default_backend

    def _prepare_cookies(self, url: str, cookies: dict | None) -> dict[str, str]:
        """Merge request cookies with stored cookies."""
        result = {}
        if self._cookie_store:
            result.update(self._cookie_store.get_for_url(url))
        if cookies:
            result.update(cookies)
        return result

    async def _prepare_cookies_async(
        self, url: str, cookies: dict | None
    ) -> dict[str, str]:
        """Merge request cookies with stored cookies (async)."""
        result = {}
        if self._cookie_store:
            result.update(await self._cookie_store.get_for_url_async(url))
        if cookies:
            result.update(cookies)
        return result

    def _store_cookies(self, url: str, response_cookies: dict[str, str]) -> None:
        """Store cookies from response."""
        if self._cookie_store is not None and response_cookies:
            self._cookie_store.update_from_response(url, response_cookies)

    async def _store_cookies_async(
        self, url: str, response_cookies: dict[str, str]
    ) -> None:
        """Store cookies from response (async)."""
        if self._cookie_store is not None and response_cookies:
            await self._cookie_store.update_from_response_async(url, response_cookies)

    def _merge_headers(self, headers: dict | None) -> dict[str, str]:
        """Merge request headers with defaults."""
        result = dict(self._default_headers)
        if headers:
            result.update(headers)
        return result

    # ========== Sync HTTP Methods ==========

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            url: Request URL.
            headers: Request headers (merged with defaults).
            params: URL query parameters.
            data: Form data for POST requests.
            json: JSON body for POST requests.
            cookies: Request cookies (merged with stored cookies).
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.
            backend: Backend to use ("httpx" or "curl").
            stealth: Apply browser fingerprinting (curl backend only).

        Returns:
            Response object.
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        backend_name = self._resolve_backend(backend)
        final_headers = self._merge_headers(headers)
        final_cookies = self._prepare_cookies(url, cookies)
        final_timeout = timeout or self._timeout
        final_proxy = proxy or self._proxy

        if backend_name == "curl":
            backend_impl = self._get_curl_backend()
            response = backend_impl.request_sync(
                method=method,
                url=url,
                headers=final_headers,
                params=params,
                data=data,
                json=json,
                cookies=final_cookies or None,
                timeout=final_timeout,
                proxy=final_proxy,
                stealth=stealth,
            )
        else:
            backend_impl = self._get_httpx_backend()
            response = backend_impl.request_sync(
                method=method,
                url=url,
                headers=final_headers,
                params=params,
                data=data,
                json=json,
                cookies=final_cookies or None,
                timeout=final_timeout,
                proxy=final_proxy,
            )

        self._store_cookies(url, response.cookies)
        self._last_response = response
        return response

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make a GET request."""
        return self.request(
            "GET",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make a POST request."""
        return self.request(
            "POST",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    def put(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make a PUT request."""
        return self.request(
            "PUT",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    def delete(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make a DELETE request."""
        return self.request(
            "DELETE",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    def patch(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make a PATCH request."""
        return self.request(
            "PATCH",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    def head(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make a HEAD request."""
        return self.request(
            "HEAD",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    def options(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an OPTIONS request."""
        return self.request(
            "OPTIONS",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    # ========== Async HTTP Methods ==========

    async def request_async(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            url: Request URL.
            headers: Request headers (merged with defaults).
            params: URL query parameters.
            data: Form data for POST requests.
            json: JSON body for POST requests.
            cookies: Request cookies (merged with stored cookies).
            timeout: Request-specific timeout.
            proxy: Request-specific proxy.
            backend: Backend to use ("httpx" or "curl").
            stealth: Apply browser fingerprinting (curl backend only).

        Returns:
            Response object.
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        backend_name = self._resolve_backend(backend)
        final_headers = self._merge_headers(headers)
        final_cookies = await self._prepare_cookies_async(url, cookies)
        final_timeout = timeout or self._timeout
        final_proxy = proxy or self._proxy

        if backend_name == "curl":
            backend_impl = self._get_curl_backend()
            response = await backend_impl.request_async(
                method=method,
                url=url,
                headers=final_headers,
                params=params,
                data=data,
                json=json,
                cookies=final_cookies or None,
                timeout=final_timeout,
                proxy=final_proxy,
                stealth=stealth,
            )
        else:
            backend_impl = self._get_httpx_backend()
            response = await backend_impl.request_async(
                method=method,
                url=url,
                headers=final_headers,
                params=params,
                data=data,
                json=json,
                cookies=final_cookies or None,
                timeout=final_timeout,
                proxy=final_proxy,
            )

        await self._store_cookies_async(url, response.cookies)
        self._last_response = response
        return response

    async def get_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async GET request."""
        return await self.request_async(
            "GET",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    async def post_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async POST request."""
        return await self.request_async(
            "POST",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    async def put_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async PUT request."""
        return await self.request_async(
            "PUT",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    async def delete_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async DELETE request."""
        return await self.request_async(
            "DELETE",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    async def patch_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async PATCH request."""
        return await self.request_async(
            "PATCH",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    async def head_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async HEAD request."""
        return await self.request_async(
            "HEAD",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    async def options_async(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        backend: Literal["httpx", "curl"] | None = None,
        stealth: bool = False,
    ) -> Response:
        """Make an async OPTIONS request."""
        return await self.request_async(
            "OPTIONS",
            url,
            headers=headers,
            params=params,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            backend=backend,
            stealth=stealth,
        )

    # ========== Helper Methods ==========

    def get_status_code(self) -> int | None:
        """Get status code from last response."""
        return self._last_response.status_code if self._last_response else None

    def get_headers(self) -> dict[str, str] | None:
        """Get headers from last response."""
        return dict(self._last_response.headers) if self._last_response else None

    def get_cookies(self) -> dict[str, str] | None:
        """Get cookies from last response."""
        return dict(self._last_response.cookies) if self._last_response else None

    def get_current_proxy(self) -> str | None:
        """Get currently configured proxy."""
        return self._proxy

    def get_elapsed(self) -> float | None:
        """Get elapsed time from last request."""
        return self._last_response.elapsed if self._last_response else None

    @property
    def last_response(self) -> Response | None:
        """Get the last response object."""
        return self._last_response

    # ========== Cookie Management ==========

    @property
    def cookies(self) -> dict[str, dict[str, str]]:
        """Get all stored cookies organized by domain."""
        if self._cookie_store:
            return self._cookie_store.get_all()
        return {}

    def clear_cookies(self, domain: str | None = None) -> None:
        """Clear cookies, optionally for specific domain."""
        if self._cookie_store:
            if domain:
                self._cookie_store.clear_domain(domain)
            else:
                self._cookie_store.clear_all()

    # ========== Header Management ==========

    def set_default_header(self, name: str, value: str) -> None:
        """Set a default header for all requests."""
        self._default_headers[name] = value

    def remove_default_header(self, name: str) -> None:
        """Remove a default header."""
        self._default_headers.pop(name, None)

    def set_proxy(self, proxy: str | None) -> None:
        """Set the default proxy."""
        self._proxy = proxy

    # ========== Context Managers ==========

    def close(self) -> None:
        """Close client and release resources."""
        if not self._closed:
            if self._httpx_backend:
                self._httpx_backend.close_sync()
            if self._curl_backend:
                self._curl_backend.close_sync()
            self._closed = True

    async def close_async(self) -> None:
        """Close client asynchronously."""
        if not self._closed:
            if self._httpx_backend:
                await self._httpx_backend.close_async()
            if self._curl_backend:
                await self._curl_backend.close_async()
            self._closed = True

    def __enter__(self) -> "HTTPClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    async def __aenter__(self) -> "HTTPClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close_async()
