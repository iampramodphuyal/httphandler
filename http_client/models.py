"""Request and Response dataclasses."""

from dataclasses import dataclass, field
from typing import Any
from http.cookies import SimpleCookie


@dataclass
class Request:
    """HTTP request representation.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, etc.).
        url: The request URL.
        headers: Request headers.
        params: URL query parameters.
        data: Form data for POST requests.
        json: JSON body for POST requests.
        cookies: Cookies to send with request.
        timeout: Request-specific timeout override.
        proxy: Request-specific proxy override.
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] | None = None
    data: dict[str, Any] | str | bytes | None = None
    json: dict[str, Any] | list | None = None
    cookies: dict[str, str] | None = None
    timeout: float | None = None
    proxy: str | None = None

    def __post_init__(self) -> None:
        """Normalize method to uppercase."""
        self.method = self.method.upper()


@dataclass
class Response:
    """HTTP response representation.

    Attributes:
        status_code: HTTP status code.
        headers: Response headers.
        content: Raw response content as bytes.
        url: Final URL after redirects.
        cookies: Cookies from response.
        elapsed: Request duration in seconds.
        request: The original request object.
        history: List of redirect responses.
    """

    status_code: int
    headers: dict[str, str]
    content: bytes
    url: str
    cookies: dict[str, str] = field(default_factory=dict)
    elapsed: float = 0.0
    request: Request | None = None
    history: list["Response"] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Decode content as UTF-8 text."""
        return self.content.decode("utf-8", errors="replace")

    @property
    def ok(self) -> bool:
        """Check if status code indicates success (2xx)."""
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        """Parse content as JSON."""
        import json as json_module
        return json_module.loads(self.content)

    def raise_for_status(self) -> None:
        """Raise HTTPError if status code indicates an error."""
        if not self.ok:
            raise HTTPError(
                f"HTTP {self.status_code} for {self.url}",
                response=self
            )


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class TransportError(HTTPClientError):
    """Error during HTTP transport (connection, timeout, etc.)."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class HTTPError(HTTPClientError):
    """HTTP error response (4xx, 5xx status codes)."""

    def __init__(self, message: str, response: Response | None = None):
        super().__init__(message)
        self.response = response


class RateLimitExceeded(HTTPClientError):
    """Rate limit exceeded error."""

    def __init__(self, domain: str, retry_after: float | None = None):
        message = f"Rate limit exceeded for {domain}"
        if retry_after:
            message += f", retry after {retry_after:.1f}s"
        super().__init__(message)
        self.domain = domain
        self.retry_after = retry_after


class AllProxiesFailed(HTTPClientError):
    """All proxies in pool have failed."""

    def __init__(self, message: str = "All proxies in pool have failed"):
        super().__init__(message)


class MaxRetriesExceeded(HTTPClientError):
    """Maximum retry attempts exceeded."""

    def __init__(self, url: str, attempts: int, last_error: Exception | None = None):
        message = f"Max retries ({attempts}) exceeded for {url}"
        super().__init__(message)
        self.url = url
        self.attempts = attempts
        self.last_error = last_error


@dataclass
class BatchResult:
    """Result of a batch operation (gather_sync or gather_async).

    Attributes:
        responses: List of successful Response objects (in order of input URLs).
        errors: Dict mapping index to exception for failed requests.
        success_count: Number of successful requests.
        failure_count: Number of failed requests.
    """

    responses: list[Response | None]
    errors: dict[int, Exception]

    @property
    def success_count(self) -> int:
        """Count of successful responses."""
        return sum(1 for r in self.responses if r is not None)

    @property
    def failure_count(self) -> int:
        """Count of failed requests."""
        return len(self.errors)

    @property
    def all_succeeded(self) -> bool:
        """Check if all requests succeeded."""
        return len(self.errors) == 0

    def raise_on_error(self) -> None:
        """Raise the first error if any requests failed."""
        if self.errors:
            first_idx = min(self.errors.keys())
            raise self.errors[first_idx]
