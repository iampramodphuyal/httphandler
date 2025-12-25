"""curl_cffi transport implementation with TLS fingerprinting support."""

from __future__ import annotations

import time
from typing import Any

from ..models import Request, Response, TransportError
from .base import BaseTransport

# Try to import curl_cffi, fall back to httpx if unavailable
try:
    from curl_cffi import requests as curl_requests
    from curl_cffi.requests import AsyncSession, Session

    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False
    curl_requests = None
    AsyncSession = None
    Session = None

# Fallback to httpx
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None


class CurlTransport(BaseTransport):
    """Transport using curl_cffi for TLS fingerprinting.

    Falls back to httpx if curl_cffi is not available.
    """

    def __init__(
        self,
        impersonate: str | None = None,
        default_timeout: float = 30.0,
        connect_timeout: float = 10.0,
    ):
        """Initialize curl transport.

        Args:
            impersonate: Browser to impersonate (e.g., "chrome120", "firefox121").
            default_timeout: Default request timeout.
            connect_timeout: Connection timeout.
        """
        super().__init__(impersonate, default_timeout, connect_timeout)

        self._using_curl = CURL_AVAILABLE
        self._sync_session: Any = None
        self._async_session: Any = None

        if not CURL_AVAILABLE and not HTTPX_AVAILABLE:
            raise ImportError(
                "Neither curl_cffi nor httpx is available. "
                "Install one of them: pip install curl_cffi or pip install httpx"
            )

    def _get_sync_session(self) -> Any:
        """Get or create sync session."""
        if self._sync_session is None:
            if self._using_curl:
                self._sync_session = Session(impersonate=self._impersonate)
            else:
                self._sync_session = httpx.Client(
                    timeout=httpx.Timeout(self._default_timeout, connect=self._connect_timeout)
                )
        return self._sync_session

    def _get_async_session(self) -> Any:
        """Get or create async session."""
        if self._async_session is None:
            if self._using_curl:
                self._async_session = AsyncSession(impersonate=self._impersonate)
            else:
                self._async_session = httpx.AsyncClient(
                    timeout=httpx.Timeout(self._default_timeout, connect=self._connect_timeout)
                )
        return self._async_session

    def _build_request_kwargs(
        self,
        request: Request,
        timeout: float | None,
        proxy: str | None,
        verify_ssl: bool,
        follow_redirects: bool,
        max_redirects: int,
    ) -> dict[str, Any]:
        """Build kwargs for the underlying HTTP library."""
        kwargs: dict[str, Any] = {
            "method": request.method,
            "url": request.url,
            "headers": request.headers or {},
        }

        if request.params:
            kwargs["params"] = request.params

        if request.data:
            kwargs["data"] = request.data

        if request.json is not None:
            kwargs["json"] = request.json

        if request.cookies:
            kwargs["cookies"] = request.cookies

        effective_timeout = timeout or request.timeout or self._default_timeout

        if self._using_curl:
            # curl_cffi specific options
            kwargs["timeout"] = effective_timeout
            kwargs["verify"] = verify_ssl
            kwargs["allow_redirects"] = follow_redirects
            kwargs["max_redirects"] = max_redirects

            if proxy or request.proxy:
                kwargs["proxy"] = proxy or request.proxy
        else:
            # httpx specific options
            kwargs["timeout"] = effective_timeout
            kwargs["follow_redirects"] = follow_redirects

            # httpx doesn't have max_redirects in request, it's set on client

        return kwargs

    def _convert_response(
        self,
        raw_response: Any,
        request: Request,
        elapsed: float,
    ) -> Response:
        """Convert library-specific response to our Response model."""
        if self._using_curl:
            # curl_cffi response
            headers = dict(raw_response.headers)
            cookies = dict(raw_response.cookies) if raw_response.cookies else {}

            return Response(
                status_code=raw_response.status_code,
                headers=headers,
                content=raw_response.content,
                url=str(raw_response.url),
                cookies=cookies,
                elapsed=elapsed,
                request=request,
            )
        else:
            # httpx response
            headers = dict(raw_response.headers)
            cookies = dict(raw_response.cookies) if raw_response.cookies else {}

            return Response(
                status_code=raw_response.status_code,
                headers=headers,
                content=raw_response.content,
                url=str(raw_response.url),
                cookies=cookies,
                elapsed=elapsed,
                request=request,
            )

    def request_sync(
        self,
        request: Request,
        timeout: float | None = None,
        proxy: str | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = 10,
    ) -> Response:
        """Execute a synchronous HTTP request.

        Args:
            request: The request to execute.
            timeout: Request timeout in seconds.
            proxy: Proxy URL to use.
            verify_ssl: Whether to verify SSL certificates.
            follow_redirects: Whether to follow redirects.
            max_redirects: Maximum number of redirects.

        Returns:
            Response object.

        Raises:
            TransportError: On connection or transport errors.
        """
        if self._closed:
            raise TransportError("Transport is closed")

        session = self._get_sync_session()
        kwargs = self._build_request_kwargs(
            request, timeout, proxy, verify_ssl, follow_redirects, max_redirects
        )

        start_time = time.monotonic()

        try:
            if self._using_curl:
                raw_response = session.request(**kwargs)
            else:
                # httpx uses different API
                raw_response = session.request(
                    method=kwargs.pop("method"),
                    url=kwargs.pop("url"),
                    **kwargs,
                )

            elapsed = time.monotonic() - start_time
            return self._convert_response(raw_response, request, elapsed)

        except Exception as e:
            error_name = type(e).__name__
            raise TransportError(
                f"Request failed: {error_name}: {str(e)}",
                original_error=e,
            ) from e

    async def request_async(
        self,
        request: Request,
        timeout: float | None = None,
        proxy: str | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = 10,
    ) -> Response:
        """Execute an asynchronous HTTP request.

        Args:
            request: The request to execute.
            timeout: Request timeout in seconds.
            proxy: Proxy URL to use.
            verify_ssl: Whether to verify SSL certificates.
            follow_redirects: Whether to follow redirects.
            max_redirects: Maximum number of redirects.

        Returns:
            Response object.

        Raises:
            TransportError: On connection or transport errors.
        """
        if self._closed:
            raise TransportError("Transport is closed")

        session = self._get_async_session()
        kwargs = self._build_request_kwargs(
            request, timeout, proxy, verify_ssl, follow_redirects, max_redirects
        )

        start_time = time.monotonic()

        try:
            if self._using_curl:
                raw_response = await session.request(**kwargs)
            else:
                # httpx async API
                raw_response = await session.request(
                    method=kwargs.pop("method"),
                    url=kwargs.pop("url"),
                    **kwargs,
                )

            elapsed = time.monotonic() - start_time
            return self._convert_response(raw_response, request, elapsed)

        except Exception as e:
            error_name = type(e).__name__
            raise TransportError(
                f"Request failed: {error_name}: {str(e)}",
                original_error=e,
            ) from e

    def close_sync(self) -> None:
        """Close synchronous resources."""
        if self._sync_session is not None:
            if self._using_curl:
                self._sync_session.close()
            else:
                self._sync_session.close()
            self._sync_session = None
        super().close_sync()

    async def close_async(self) -> None:
        """Close asynchronous resources."""
        if self._async_session is not None:
            if self._using_curl:
                await self._async_session.close()
            else:
                await self._async_session.aclose()
            self._async_session = None
        await super().close_async()

    @property
    def using_curl_cffi(self) -> bool:
        """Check if using curl_cffi (True) or httpx fallback (False)."""
        return self._using_curl

    @property
    def backend_name(self) -> str:
        """Get name of the underlying HTTP library."""
        return "curl_cffi" if self._using_curl else "httpx"
