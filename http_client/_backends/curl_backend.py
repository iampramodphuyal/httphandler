"""curl_cffi-based HTTP backend with TLS fingerprinting."""

from __future__ import annotations

from typing import Any

from ..models import Request, Response, TransportError

# Optional curl_cffi import
try:
    from curl_cffi.requests import Session, AsyncSession
    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False
    Session = None
    AsyncSession = None


class CurlBackend:
    """curl_cffi wrapper with browser fingerprinting support.

    Provides TLS fingerprinting via curl_cffi's impersonate feature.
    """

    def __init__(
        self,
        profile: str = "chrome_120",
        timeout: float = 30.0,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
    ):
        """Initialize curl backend.

        Args:
            profile: Browser profile name for impersonation.
            timeout: Default request timeout in seconds.
            verify_ssl: Whether to verify SSL certificates.
            follow_redirects: Whether to follow redirects.

        Raises:
            ImportError: If curl_cffi is not installed.
        """
        if not CURL_AVAILABLE:
            raise ImportError(
                "curl_cffi is required for curl backend. "
                "Install with: pip install curl_cffi"
            )

        self._profile_name = profile
        self._impersonate = self._get_impersonate_string(profile)
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._follow_redirects = follow_redirects

        # Lazy-initialized sessions
        self._sync_session: Session | None = None
        self._async_session: AsyncSession | None = None

        # Header generator for stealth mode
        self._header_generator = None

    def _get_impersonate_string(self, profile: str) -> str:
        """Convert profile name to curl_cffi impersonate string.

        Args:
            profile: Profile name like 'chrome_120'.

        Returns:
            Impersonate string like 'chrome120'.
        """
        # Map profile names to curl_cffi impersonate strings
        profile_map = {
            "chrome_120": "chrome120",
            "chrome_119": "chrome119",
            "chrome_118": "chrome118",
            "firefox_121": "firefox121",
            "firefox_120": "firefox120",
            "firefox_117": "firefox117",
            "safari_17": "safari17_0",
            "safari_16": "safari16_0",
            "safari_15": "safari15_5",
            "edge_120": "edge120",
            "edge_119": "edge119",
        }
        return profile_map.get(profile, profile.replace("_", ""))

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
                # Use browserforge by default, with fallback to static profiles
                self._header_generator = create_header_generator(
                    use_browserforge=True,
                    browser=self._get_browser_from_profile(),
                )
            except ImportError:
                # Fingerprint module not available, use None
                pass
        return self._header_generator

    def _get_sync_session(self) -> Session:
        """Get or create sync session (lazy initialization)."""
        if self._sync_session is None:
            self._sync_session = Session(
                impersonate=self._impersonate,
                timeout=self._timeout,
                verify=self._verify_ssl,
            )
        return self._sync_session

    def _get_async_session(self) -> AsyncSession:
        """Get or create async session (lazy initialization)."""
        if self._async_session is None:
            self._async_session = AsyncSession(
                impersonate=self._impersonate,
                timeout=self._timeout,
                verify=self._verify_ssl,
            )
        return self._async_session

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
                # Fallback to custom headers if generator fails
                pass

        return headers or {}

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
            proxy: Proxy URL.
            stealth: Apply browser fingerprinting headers.

        Returns:
            Response object.

        Raises:
            TransportError: On connection/transport errors.
        """
        final_headers = self._prepare_headers(url, method, headers, stealth)

        try:
            session = self._get_sync_session()
            resp = session.request(
                method=method,
                url=url,
                headers=final_headers or None,
                params=params,
                data=data,
                json=json,
                cookies=cookies,
                timeout=timeout or self._timeout,
                proxies={"all": proxy} if proxy else None,
                allow_redirects=self._follow_redirects,
            )

            return self._convert_response(resp, method, url)

        except Exception as e:
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
            proxy: Proxy URL.
            stealth: Apply browser fingerprinting headers.

        Returns:
            Response object.

        Raises:
            TransportError: On connection/transport errors.
        """
        final_headers = self._prepare_headers(url, method, headers, stealth)

        try:
            session = self._get_async_session()
            resp = await session.request(
                method=method,
                url=url,
                headers=final_headers or None,
                params=params,
                data=data,
                json=json,
                cookies=cookies,
                timeout=timeout or self._timeout,
                proxies={"all": proxy} if proxy else None,
                allow_redirects=self._follow_redirects,
            )

            return self._convert_response(resp, method, url)

        except Exception as e:
            raise TransportError(str(e), original_error=e) from e

    def _convert_response(self, resp: Any, method: str, url: str) -> Response:
        """Convert curl_cffi response to our Response model.

        Args:
            resp: curl_cffi Response object.
            method: Original request method.
            url: Original request URL.

        Returns:
            Response object.
        """
        # Extract cookies from response
        cookies = {}
        if hasattr(resp, "cookies"):
            for name, value in resp.cookies.items():
                cookies[name] = value

        return Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
            url=str(resp.url),
            cookies=cookies,
            elapsed=resp.elapsed.total_seconds() if hasattr(resp, "elapsed") and hasattr(resp.elapsed, "total_seconds") else (resp.elapsed if hasattr(resp, "elapsed") else 0.0),
            request=Request(method=method, url=url),
            history=[],
        )

    def close_sync(self) -> None:
        """Close sync session."""
        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None

    async def close_async(self) -> None:
        """Close async session."""
        if self._async_session:
            await self._async_session.close()
            self._async_session = None
