"""Simple HTTP handler with session management and helper methods.

This module provides a simplified interface for HTTP requests with:
- Session persistence control
- Response helper methods
- Header and proxy management
- Streaming support
- Context managers for scoped sessions

Basic usage:

    from http_client import HTTPHandler

    handler = HTTPHandler()
    resp = handler.get("https://example.com", headers={"User-Agent": "MyApp/1.0"})

    # Access last response info
    print(handler.get_status_code())
    print(handler.get_cookies())

    # Session management
    handler.persist_session = True
    handler.get("https://example.com/login")
    handler.get("https://example.com/dashboard")  # Cookies maintained
    handler.reset_session()  # Clear for fresh start
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Literal

from .models import Request, Response, HTTPClientError
from .transport import CurlTransport
from .safety import CookieStore


class NoResponseError(HTTPClientError):
    """Raised when accessing response data before making a request."""

    def __init__(self) -> None:
        super().__init__("No response available. Make a request first.")


class HTTPHandler:
    """Simple HTTP handler with session management.

    Provides a clean interface for making HTTP requests with:
    - Optional session persistence (cookies)
    - Response helper methods
    - Header and proxy management
    - Streaming support
    - Context managers

    Args:
        persist_session: Whether to persist cookies across requests. Default False.
        timeout: Request timeout in seconds.
        connect_timeout: Connection timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        http_version: HTTP version - "1.1", "2", or "auto".
        proxy: Proxy URL (e.g., "socks5://host:port").
        max_retries: Maximum retry attempts on failure.
        headers: Default headers to send with every request.
        retry_codes: HTTP status codes that trigger a retry.
        retry_backoff_base: Base for exponential backoff calculation.
    """

    def __init__(
        self,
        persist_session: bool = False,
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        verify_ssl: bool = True,
        http_version: Literal["1.1", "2", "auto"] = "auto",
        proxy: str | None = None,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
        retry_codes: tuple[int, ...] = (429, 500, 502, 503, 504),
        retry_backoff_base: float = 2.0,
    ) -> None:
        # Configuration
        self._timeout = timeout
        self._connect_timeout = connect_timeout
        self._verify_ssl = verify_ssl
        self._http_version = http_version
        self._max_retries = max_retries
        self._retry_codes = retry_codes
        self._retry_backoff_base = retry_backoff_base

        # Proxy state
        self._proxy: str | None = proxy
        self._proxy_enabled: bool = proxy is not None

        # Session state
        self._persist_session = persist_session
        self._cookie_store: CookieStore | None = CookieStore() if persist_session else None
        self._default_headers: dict[str, str] = dict(headers) if headers else {}

        # Last response for helper methods
        self._last_response: Response | None = None

        # Transport
        self._transport = CurlTransport(
            default_timeout=timeout,
            connect_timeout=connect_timeout,
            http_version=http_version,
        )
        self._closed = False

    # -------------------------------------------------------------------------
    # HTTP Methods
    # -------------------------------------------------------------------------

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make a GET request."""
        return self._request("GET", url, headers=headers, params=params, **kwargs)

    def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make a POST request."""
        return self._request("POST", url, headers=headers, data=data, json=json, **kwargs)

    def put(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make a PUT request."""
        return self._request("PUT", url, headers=headers, data=data, json=json, **kwargs)

    def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make a DELETE request."""
        return self._request("DELETE", url, headers=headers, **kwargs)

    def patch(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make a PATCH request."""
        return self._request("PATCH", url, headers=headers, data=data, json=json, **kwargs)

    def head(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make a HEAD request."""
        return self._request("HEAD", url, headers=headers, **kwargs)

    def options(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make an OPTIONS request."""
        return self._request("OPTIONS", url, headers=headers, **kwargs)

    # -------------------------------------------------------------------------
    # Response Helper Methods
    # -------------------------------------------------------------------------

    def get_status_code(self) -> int:
        """Get the status code from the last response.

        Returns:
            HTTP status code.

        Raises:
            NoResponseError: If no request has been made yet.
        """
        if self._last_response is None:
            raise NoResponseError()
        return self._last_response.status_code

    def get_cookies(self) -> dict[str, str]:
        """Get cookies from the last response.

        Returns:
            Dict of cookies from the response.

        Raises:
            NoResponseError: If no request has been made yet.
        """
        if self._last_response is None:
            raise NoResponseError()
        return dict(self._last_response.cookies)

    def get_headers(self) -> dict[str, str]:
        """Get headers from the last response.

        Returns:
            Dict of response headers.

        Raises:
            NoResponseError: If no request has been made yet.
        """
        if self._last_response is None:
            raise NoResponseError()
        return dict(self._last_response.headers)

    def get_bandwidth(self) -> float:
        """Get bandwidth of the last request in bytes/second.

        Returns:
            Bandwidth in bytes per second.

        Raises:
            NoResponseError: If no request has been made yet.
        """
        if self._last_response is None:
            raise NoResponseError()
        if self._last_response.elapsed <= 0:
            return 0.0
        return len(self._last_response.content) / self._last_response.elapsed

    def get_elapsed(self) -> float:
        """Get elapsed time of the last request in seconds.

        Returns:
            Request duration in seconds.

        Raises:
            NoResponseError: If no request has been made yet.
        """
        if self._last_response is None:
            raise NoResponseError()
        return self._last_response.elapsed

    def get_content_length(self) -> int:
        """Get content length of the last response in bytes.

        Returns:
            Content length in bytes.

        Raises:
            NoResponseError: If no request has been made yet.
        """
        if self._last_response is None:
            raise NoResponseError()
        return len(self._last_response.content)

    def get_response(self) -> Response:
        """Get the full last response object.

        Returns:
            The last Response object.

        Raises:
            NoResponseError: If no request has been made yet.
        """
        if self._last_response is None:
            raise NoResponseError()
        return self._last_response

    # -------------------------------------------------------------------------
    # Session Control
    # -------------------------------------------------------------------------

    @property
    def persist_session(self) -> bool:
        """Whether session persistence is enabled."""
        return self._persist_session

    @persist_session.setter
    def persist_session(self, value: bool) -> None:
        """Enable or disable session persistence.

        When enabling, creates a new cookie store.
        When disabling, clears and removes the cookie store.
        """
        if value and not self._persist_session:
            # Enabling persistence
            self._cookie_store = CookieStore()
        elif not value and self._persist_session:
            # Disabling persistence
            self._cookie_store = None
        self._persist_session = value

    def reset_session(self) -> None:
        """Reset session state (clear cookies and stored response)."""
        if self._cookie_store is not None:
            self._cookie_store.clear_all()
        self._last_response = None

    def clear_cookies(self, domain: str | None = None) -> None:
        """Clear cookies, optionally for a specific domain.

        Args:
            domain: If provided, only clear cookies for this domain.
                   If None, clears all cookies.
        """
        if self._cookie_store is not None:
            if domain:
                self._cookie_store.clear_domain(domain)
            else:
                self._cookie_store.clear_all()

    # -------------------------------------------------------------------------
    # Header Management
    # -------------------------------------------------------------------------

    def set_headers(self, headers: dict[str, str]) -> None:
        """Set default headers for all requests.

        These headers are merged with request-specific headers.
        Request headers take precedence over defaults.

        Args:
            headers: Dict of header name to value.
        """
        self._default_headers = dict(headers)

    def get_default_headers(self) -> dict[str, str]:
        """Get the current default headers.

        Returns:
            Dict of default headers.
        """
        return dict(self._default_headers)

    def clear_headers(self) -> None:
        """Clear all default headers."""
        self._default_headers = {}

    def add_header(self, name: str, value: str) -> None:
        """Add or update a single default header.

        Args:
            name: Header name.
            value: Header value.
        """
        self._default_headers[name] = value

    def remove_header(self, name: str) -> None:
        """Remove a default header.

        Args:
            name: Header name to remove.
        """
        self._default_headers.pop(name, None)

    # -------------------------------------------------------------------------
    # Proxy Control
    # -------------------------------------------------------------------------

    def set_proxy(self, proxy: str | None) -> None:
        """Set the proxy URL.

        Args:
            proxy: Proxy URL (e.g., "socks5://host:port") or None to clear.
        """
        self._proxy = proxy
        self._proxy_enabled = proxy is not None

    def enable_proxy(self) -> None:
        """Enable the configured proxy."""
        if self._proxy:
            self._proxy_enabled = True

    def disable_proxy(self) -> None:
        """Temporarily disable the proxy without clearing it."""
        self._proxy_enabled = False

    @property
    def proxy_enabled(self) -> bool:
        """Whether proxy is currently enabled."""
        return self._proxy_enabled and self._proxy is not None

    @property
    def proxy(self) -> str | None:
        """Get the configured proxy URL."""
        return self._proxy

    # -------------------------------------------------------------------------
    # Streaming
    # -------------------------------------------------------------------------

    def stream(
        self,
        url: str,
        chunk_size: int = 8192,
        callback: Callable[[bytes, int, int | None], None] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Iterator[bytes]:
        """Stream a response in chunks.

        Useful for downloading large files without loading into memory.

        Args:
            url: The URL to request.
            chunk_size: Size of each chunk in bytes.
            callback: Optional callback(chunk, total_downloaded, content_length).
            headers: Request headers.
            **kwargs: Additional request arguments.

        Yields:
            Chunks of response content.

        Example:
            for chunk in handler.stream("https://example.com/file.zip"):
                file.write(chunk)
        """
        # For now, we fetch the full response and yield in chunks
        # This is because curl_cffi doesn't expose streaming directly
        # In a production implementation, you'd want native streaming support
        response = self._request("GET", url, headers=headers, **kwargs)
        content = response.content
        content_length = len(content)
        total_downloaded = 0

        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            total_downloaded += len(chunk)

            if callback:
                callback(chunk, total_downloaded, content_length)

            yield chunk

    # -------------------------------------------------------------------------
    # Context Managers
    # -------------------------------------------------------------------------

    @contextmanager
    def session(self) -> Iterator["HTTPHandler"]:
        """Context manager for a scoped session.

        Creates a temporary session that auto-resets on exit.
        If persist_session was already True, cookies from before
        entering the context are preserved.

        Example:
            with handler.session() as s:
                s.get("https://example.com/step1")
                s.get("https://example.com/step2")
            # Session automatically reset on exit
        """
        import copy

        # Save current state
        old_persist = self._persist_session
        old_cookies: dict | None = None

        if self._cookie_store:
            # Deep copy the cookies dict (dict of dicts)
            old_cookies = {
                domain: dict(cookies)
                for domain, cookies in self._cookie_store._cookies.items()
            }

        # Enable session for this scope
        self.persist_session = True

        try:
            yield self
        finally:
            # Restore previous state
            if old_persist:
                # Was already persisting - restore the old cookies
                if self._cookie_store and old_cookies is not None:
                    self._cookie_store._cookies.clear()
                    for domain, cookies in old_cookies.items():
                        self._cookie_store._cookies[domain] = cookies
            else:
                # Was not persisting - reset and disable
                self.reset_session()
                self._persist_session = False
                self._cookie_store = None

    def __enter__(self) -> "HTTPHandler":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and cleanup resources."""
        self.close()

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the handler and release resources."""
        if not self._closed:
            self._transport.close_sync()
            self._closed = True

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        json: dict[str, Any] | list | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Execute an HTTP request.

        Args:
            method: HTTP method.
            url: Request URL.
            headers: Request headers.
            params: URL query parameters.
            data: Form data.
            json: JSON body.
            cookies: Request cookies.
            timeout: Request timeout override.

        Returns:
            Response object.
        """
        if self._closed:
            raise HTTPClientError("Handler is closed")

        # Warn if no headers provided
        final_headers = {**self._default_headers}
        if headers:
            final_headers.update(headers)

        if not final_headers:
            warnings.warn(
                "No headers provided. Request may be detected as bot traffic. "
                "Consider setting headers like User-Agent.",
                UserWarning,
                stacklevel=3,
            )

        # Merge cookies from store with request cookies
        final_cookies = {}
        if self._cookie_store:
            final_cookies.update(self._cookie_store.get_for_url(url))
        if cookies:
            final_cookies.update(cookies)

        # Create request
        request = Request(
            method=method,
            url=url,
            headers=final_headers,
            params=params,
            data=data,
            json=json,
            cookies=final_cookies if final_cookies else None,
            timeout=timeout or self._timeout,
            proxy=self._proxy if self._proxy_enabled else None,
        )

        # Execute with retry
        response = self._execute_with_retry(request)

        # Store response cookies
        if self._cookie_store and response.cookies:
            self._cookie_store.update_from_response(url, response.cookies)

        # Store last response
        self._last_response = response

        return response

    def _execute_with_retry(self, request: Request) -> Response:
        """Execute request with retry logic.

        Args:
            request: The request to execute.

        Returns:
            Response object.
        """
        import time
        from .models import TransportError, MaxRetriesExceeded

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.request_sync(
                    request=request,
                    timeout=request.timeout or self._timeout,
                    proxy=request.proxy,
                    verify_ssl=self._verify_ssl,
                    follow_redirects=True,
                    max_redirects=10,
                )

                # Check if we should retry based on status code
                if response.status_code in self._retry_codes:
                    if attempt < self._max_retries:
                        backoff = self._retry_backoff_base ** attempt
                        time.sleep(backoff)
                        continue

                return response

            except TransportError as e:
                last_error = e
                if attempt < self._max_retries:
                    backoff = self._retry_backoff_base ** attempt
                    time.sleep(backoff)
                    continue
                raise

        raise MaxRetriesExceeded(
            url=request.url,
            attempts=self._max_retries + 1,
            last_error=last_error,
        )
