"""httpx-based HTTP backend."""

from __future__ import annotations

from typing import Any

import httpx

from ..models import Request, Response, TransportError


class HttpxBackend:
    """Simple httpx wrapper for HTTP requests.

    Provides both sync and async methods with lazy session initialization.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        http2: bool = True,
        follow_redirects: bool = True,
    ):
        """Initialize httpx backend.

        Args:
            timeout: Default request timeout in seconds.
            verify_ssl: Whether to verify SSL certificates.
            http2: Whether to use HTTP/2.
            follow_redirects: Whether to follow redirects.
        """
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._http2 = http2
        self._follow_redirects = follow_redirects
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

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

        Returns:
            Response object.

        Raises:
            TransportError: On connection/transport errors.
        """
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
                        headers=headers,
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
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    cookies=cookies,
                    timeout=timeout,
                )

            return self._convert_response(resp, method, url)

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

        Returns:
            Response object.

        Raises:
            TransportError: On connection/transport errors.
        """
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
                        headers=headers,
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
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    cookies=cookies,
                    timeout=timeout,
                )

            return self._convert_response(resp, method, url)

        except httpx.HTTPError as e:
            raise TransportError(str(e), original_error=e) from e

    def _convert_response(
        self,
        httpx_resp: httpx.Response,
        method: str,
        url: str,
    ) -> Response:
        """Convert httpx.Response to our Response model.

        Args:
            httpx_resp: httpx Response object.
            method: Original request method.
            url: Original request URL.

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
            request=Request(method=method, url=url),
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
