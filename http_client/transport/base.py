"""Abstract transport protocol for HTTP requests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from ..models import Request, Response


@runtime_checkable
class Transport(Protocol):
    """Protocol defining the transport interface.

    Transports handle the actual HTTP communication and must implement
    both synchronous and asynchronous request methods.
    """

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
        ...

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
        ...

    def close_sync(self) -> None:
        """Close synchronous resources."""
        ...

    async def close_async(self) -> None:
        """Close asynchronous resources."""
        ...


class BaseTransport(ABC):
    """Abstract base class for transport implementations.

    Provides common functionality and enforces the transport interface.
    """

    def __init__(
        self,
        impersonate: str | None = None,
        default_timeout: float = 30.0,
        connect_timeout: float = 10.0,
    ):
        """Initialize transport.

        Args:
            impersonate: Browser to impersonate (for TLS fingerprinting).
            default_timeout: Default request timeout.
            connect_timeout: Connection timeout.
        """
        self._impersonate = impersonate
        self._default_timeout = default_timeout
        self._connect_timeout = connect_timeout
        self._closed = False

    @property
    def is_closed(self) -> bool:
        """Check if transport has been closed."""
        return self._closed

    @abstractmethod
    def request_sync(
        self,
        request: Request,
        timeout: float | None = None,
        proxy: str | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = 10,
    ) -> Response:
        """Execute a synchronous HTTP request."""
        raise NotImplementedError

    @abstractmethod
    async def request_async(
        self,
        request: Request,
        timeout: float | None = None,
        proxy: str | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = 10,
    ) -> Response:
        """Execute an asynchronous HTTP request."""
        raise NotImplementedError

    def close_sync(self) -> None:
        """Close synchronous resources."""
        self._closed = True

    async def close_async(self) -> None:
        """Close asynchronous resources."""
        self._closed = True

    def __enter__(self) -> "BaseTransport":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close_sync()

    async def __aenter__(self) -> "BaseTransport":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close_async()
