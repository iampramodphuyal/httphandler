"""HTTP client package with unified interface.

Simple usage:
    from http_client import HTTPClient

    client = HTTPClient()
    response = client.get("https://example.com")
    print(response.text)

With cookie persistence:
    client = HTTPClient(persist_cookies=True)
    client.post("https://example.com/login", json={"user": "..."})
    client.get("https://example.com/dashboard")  # Cookies included

Per-request backend switching:
    # Use httpx (default) for most requests
    response = client.get("https://api.example.com")

    # Switch to curl for stealth mode
    response = client.get(
        "https://protected-site.com",
        backend="curl",
        stealth=True,
    )

Async usage:
    async with HTTPClient() as client:
        response = await client.get_async("https://example.com")
"""

from .client import HTTPClient
from .models import (
    Request,
    Response,
    HTTPClientError,
    TransportError,
    HTTPError,
    MaxRetriesExceeded,
)

__version__ = "0.5.2"

__all__ = [
    "HTTPClient",
    "Request",
    "Response",
    "HTTPClientError",
    "TransportError",
    "HTTPError",
    "MaxRetriesExceeded",
]
