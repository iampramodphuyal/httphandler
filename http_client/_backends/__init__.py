"""Internal backend implementations for HTTPClient."""

from .httpx_backend import HttpxBackend
from .curl_backend import CurlBackend, CURL_AVAILABLE

__all__ = ["HttpxBackend", "CurlBackend", "CURL_AVAILABLE"]
