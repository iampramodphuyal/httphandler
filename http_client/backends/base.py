"""Abstract backend protocol for execution models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Protocol, Sequence, runtime_checkable

from ..config import ClientConfig
from ..models import BatchResult, Request, Response


@runtime_checkable
class Backend(Protocol):
    """Protocol defining the backend interface.

    Backends handle the execution model (async vs threaded) and coordinate
    with transport, rate limiting, proxy management, and cookie storage.
    """

    def execute_sync(self, request: Request) -> Response:
        """Execute a single request synchronously.

        Args:
            request: The request to execute.

        Returns:
            Response object.
        """
        ...

    async def execute_async(self, request: Request) -> Response:
        """Execute a single request asynchronously.

        Args:
            request: The request to execute.

        Returns:
            Response object.
        """
        ...

    def gather_sync(
        self,
        requests: Sequence[Request],
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using thread pool.

        Args:
            requests: Sequence of requests to execute.
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        ...

    async def gather_async(
        self,
        requests: Sequence[Request],
        concurrency: int | None = None,
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using asyncio with semaphore.

        Args:
            requests: Sequence of requests to execute.
            concurrency: Max concurrent requests (None for config default).
            stop_on_error: Whether to stop on first error.

        Returns:
            BatchResult with responses and errors.
        """
        ...

    def close(self) -> None:
        """Close backend resources synchronously."""
        ...

    async def close_async(self) -> None:
        """Close backend resources asynchronously."""
        ...


class BaseBackend(ABC):
    """Abstract base class for backend implementations.

    Provides common functionality for request execution including:
    - Rate limiting integration
    - Proxy selection
    - Cookie management
    - Retry logic
    - Header generation
    """

    def __init__(self, config: ClientConfig):
        """Initialize backend with configuration.

        Args:
            config: Client configuration.
        """
        self._config = config
        self._closed = False

    @property
    def config(self) -> ClientConfig:
        """Get backend configuration."""
        return self._config

    @property
    def is_closed(self) -> bool:
        """Check if backend has been closed."""
        return self._closed

    @abstractmethod
    def execute_sync(self, request: Request) -> Response:
        """Execute a single request synchronously."""
        raise NotImplementedError

    @abstractmethod
    async def execute_async(self, request: Request) -> Response:
        """Execute a single request asynchronously."""
        raise NotImplementedError

    @abstractmethod
    def gather_sync(
        self,
        requests: Sequence[Request],
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using thread pool."""
        raise NotImplementedError

    @abstractmethod
    async def gather_async(
        self,
        requests: Sequence[Request],
        concurrency: int | None = None,
        stop_on_error: bool = False,
    ) -> BatchResult:
        """Execute multiple requests using asyncio."""
        raise NotImplementedError

    def close(self) -> None:
        """Close backend resources synchronously."""
        self._closed = True

    async def close_async(self) -> None:
        """Close backend resources asynchronously."""
        self._closed = True

    def __enter__(self) -> "BaseBackend":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> "BaseBackend":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close_async()
