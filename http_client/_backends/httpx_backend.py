"""httpx-based HTTP backend."""

from __future__ import annotations

from typing import Any

import httpx

from ..models import Request, Response, TransportError


class HttpxBackend:
    """Simple httpx wrapper for HTTP requests.

    Provides both sync and async methods with lazy session initialization.
    Supports optional browserforge header generation for stealth mode.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        http2: bool = True,
        follow_redirects: bool = True,
        profile: str = "chrome_120",
    ):
        """Initialize httpx backend.

        Args:
            timeout: Default request timeout in seconds.
            verify_ssl: Whether to verify SSL certificates.
            http2: Whether to use HTTP/2.
            follow_redirects: Whether to follow redirects.
            profile: Browser profile for stealth mode header generation.
        """
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._http2 = http2
        self._follow_redirects = follow_redirects
        self._profile_name = profile
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._header_generator = None

    def _get_browser_from_profile(self) -> str:
        """Extract browser name from profile (e.g., 'chrome_120' -> 'chrome')."""
        return self._profile_name.split("_")[0]

    def _get_header_generator(self):
        """Get or create header generator (lazy initialization).

        Uses browserforge by default for realistic headers, with fallback
        to static profiles if browserforge is not installed.
        """
        if self._header_generator is None:
            try:
                from .._fingerprint import create_header_generator
                self._header_generator = create_header_generator(
                    use_browserforge=True,
                    browser=self._get_browser_from_profile(),
                )
            except ImportError:
                pass
        return self._header_generator

    def _prepare_headers(
        self,
        url: str,
        method: str,
        headers: dict[str, str] | None,
        stealth: bool,
    ) -> dict[str, str]:
        """Prepare headers with optional stealth mode.

        Args:
            url: Request URL.
            method: HTTP method.
            headers: Custom headers.
            stealth: Whether to apply browser fingerprinting.

        Returns:
            Final headers dict.
        """
        if not stealth:
            return headers or {}

        generator = self._get_header_generator()
        if generator:
            try:
                return generator.generate(
                    url=url,
                    method=method,
                    custom_headers=headers,
                )
            except Exception:
                pass

        return headers or {}

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync client (lazy initialization)."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                timeout=self._timeout,
                verify=self._verify_ssl,
                http2=self._http2,
                follow_redirects=self._follow_redirects,
            )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async client (lazy initialization)."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self._timeout,
                verify=self._verify_ssl,
                http2=self._http2,
                follow_redirects=self._follow_redirects,
            )
        return self._async_client

    def request_sync(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        stealth: bool = False,
    ) -> Response:
        """Execute synchronous HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data.
            json: JSON body.
            cookies: Request cookies.
            timeout: Request-specific timeout.
            proxy: Proxy URL (creates new client if provided).
            stealth: Apply browser fingerprinting headers.

        Returns:
            Response object.

        Raises:
            TransportError: On connection/transport errors.
        """
        final_headers = self._prepare_headers(url, method, headers, stealth)

        try:
            # Use proxy-specific client if proxy provided
            if proxy:
                with httpx.Client(
                    timeout=timeout or self._timeout,
                    verify=self._verify_ssl,
                    http2=self._http2,
                    follow_redirects=self._follow_redirects,
                    proxy=proxy,
                ) as client:
                    resp = client.request(
                        method=method,
                        url=url,
                        headers=final_headers or None,
                        params=params,
                        data=data,
                        json=json,
                        cookies=cookies,
                    )
            else:
                client = self._get_sync_client()
                resp = client.request(
                    method=method,
                    url=url,
                    headers=final_headers or None,
                    params=params,
                    data=data,
                    json=json,
                    cookies=cookies,
                    timeout=timeout,
                )

            return self._convert_response(
                resp, method, url,
                headers=final_headers,
                params=params,
                data=data,
                json=json,
                cookies=cookies,
                timeout=timeout,
                proxy=proxy,
            )

        except httpx.HTTPError as e:
            raise TransportError(str(e), original_error=e) from e

    async def request_async(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
        stealth: bool = False,
    ) -> Response:
        """Execute asynchronous HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data.
            json: JSON body.
            cookies: Request cookies.
            timeout: Request-specific timeout.
            proxy: Proxy URL (creates new client if provided).
            stealth: Apply browser fingerprinting headers.

        Returns:
            Response object.

        Raises:
            TransportError: On connection/transport errors.
        """
        final_headers = self._prepare_headers(url, method, headers, stealth)

        try:
            # Use proxy-specific client if proxy provided
            if proxy:
                async with httpx.AsyncClient(
                    timeout=timeout or self._timeout,
                    verify=self._verify_ssl,
                    http2=self._http2,
                    follow_redirects=self._follow_redirects,
                    proxy=proxy,
                ) as client:
                    resp = await client.request(
                        method=method,
                        url=url,
                        headers=final_headers or None,
                        params=params,
                        data=data,
                        json=json,
                        cookies=cookies,
                    )
            else:
                client = self._get_async_client()
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=final_headers or None,
                    params=params,
                    data=data,
                    json=json,
                    cookies=cookies,
                    timeout=timeout,
                )

            return self._convert_response(
                resp, method, url,
                headers=final_headers,
                params=params,
                data=data,
                json=json,
                cookies=cookies,
                timeout=timeout,
                proxy=proxy,
            )

        except httpx.HTTPError as e:
            raise TransportError(str(e), original_error=e) from e

    def _convert_response(
        self,
        httpx_resp: httpx.Response,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> Response:
        """Convert httpx.Response to our Response model.

        Args:
            httpx_resp: httpx Response object.
            method: Original request method.
            url: Original request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data.
            json: JSON body.
            cookies: Request cookies.
            timeout: Request timeout.
            proxy: Proxy URL.

        Returns:
            Response object.
        """
        return Response(
            status_code=httpx_resp.status_code,
            headers=dict(httpx_resp.headers),
            content=httpx_resp.content,
            url=str(httpx_resp.url),
            cookies=dict(httpx_resp.cookies),
            elapsed=httpx_resp.elapsed.total_seconds(),
            request=Request(
                method=method,
                url=url,
                headers=headers or {},
                params=params,
                data=data,
                json=json,
                cookies=cookies,
                timeout=timeout,
                proxy=proxy,
            ),
            history=[],
        )

    def close_sync(self) -> None:
        """Close sync client."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    async def close_async(self) -> None:
        """Close async client."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
