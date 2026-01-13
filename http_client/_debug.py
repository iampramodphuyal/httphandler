"""Debug/verbose mode for HTTPClient."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Callable, TextIO


@dataclass
class DebugInfo:
    """Debug information for a request/response cycle.

    Captures all relevant details for debugging web scraping requests,
    including headers, cookies, proxy, timing, and TLS info.
    """

    # Request info
    timestamp: datetime
    method: str
    url: str

    # Backend info
    backend: str  # "httpx" or "curl"
    stealth_mode: bool = False
    profile: str | None = None
    http_version: str = "auto"

    # Request details
    request_headers: dict[str, str] = field(default_factory=dict)
    request_headers_order: list[str] = field(default_factory=list)
    cookies_sent: dict[str, str] = field(default_factory=dict)
    proxy_used: str | None = None

    # Response details (populated after request)
    final_url: str | None = None
    status_code: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    cookies_received: dict[str, str] = field(default_factory=dict)
    content_length: int = 0
    content_preview: str | None = None
    elapsed: float = 0.0

    # TLS/curl info
    impersonate: str | None = None

    # Error info
    error: str | None = None


class DebugOutput:
    """Handles verbose output formatting and dispatch."""

    def __init__(
        self,
        enabled: bool = False,
        output: TextIO | None = None,
        callback: Callable[[DebugInfo], None] | None = None,
    ):
        """Initialize debug output handler.

        Args:
            enabled: Whether verbose output is enabled.
            output: Output stream (defaults to stderr).
            callback: Optional callback for programmatic capture.
        """
        self.enabled = enabled
        self.output = output or sys.stderr
        self.callback = callback

    def log_request(self, info: DebugInfo) -> None:
        """Log debug info for a request/response cycle.

        Args:
            info: Debug information to log.
        """
        if not self.enabled:
            return

        # Call user callback if set
        if self.callback:
            self.callback(info)

        # Print formatted output
        self._print_formatted(info)

    def _print_formatted(self, info: DebugInfo) -> None:
        """Print formatted debug output to stream.

        Args:
            info: Debug information to format and print.
        """
        out = self.output
        sep = "=" * 80

        # Header
        out.write(f"\n{sep}\n")
        out.write(f"[{info.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ")
        out.write(f"{info.method} {info.url}\n")
        out.write(f"{sep}\n")

        # Backend info line
        parts = [f"Backend: {info.backend}"]
        if info.stealth_mode:
            parts.append("Stealth: ON")
            if info.profile:
                parts.append(f"Profile: {info.profile}")
        else:
            parts.append("Stealth: OFF")
        parts.append(f"HTTP: {info.http_version}")
        out.write(" | ".join(parts) + "\n")

        # Request headers
        if info.request_headers:
            out.write("\n> Request Headers:\n")
            for header in info.request_headers_order or info.request_headers.keys():
                if header in info.request_headers:
                    value = info.request_headers[header]
                    # Truncate long values
                    if len(value) > 80:
                        value = value[:77] + "..."
                    out.write(f"  {header}: {value}\n")

        # Cookies sent
        if info.cookies_sent:
            cookies_str = "; ".join(f"{k}={v}" for k, v in info.cookies_sent.items())
            if len(cookies_str) > 100:
                cookies_str = cookies_str[:97] + "..."
            out.write(f"\n> Cookies Sent: {cookies_str}\n")

        # Proxy
        if info.proxy_used:
            # Mask password in proxy URL
            proxy_display = self._mask_proxy_password(info.proxy_used)
            out.write(f"> Proxy: {proxy_display}\n")

        # Response section
        out.write("\n" + "-" * 80 + "\n")

        if info.error:
            out.write(f"< ERROR: {info.error}\n")
        elif info.status_code is not None:
            out.write(f"< HTTP {info.status_code}")
            if info.elapsed:
                out.write(f"  [{info.elapsed:.3f}s]")
            out.write("\n")

            if info.final_url and info.final_url != info.url:
                out.write(f"< Redirected to: {info.final_url}\n")

            # Response headers
            if info.response_headers:
                out.write("\n< Response Headers:\n")
                for header, value in info.response_headers.items():
                    if len(value) > 80:
                        value = value[:77] + "..."
                    out.write(f"  {header}: {value}\n")

            # Cookies received
            if info.cookies_received:
                cookies_str = "; ".join(
                    f"{k}={v}" for k, v in info.cookies_received.items()
                )
                if len(cookies_str) > 100:
                    cookies_str = cookies_str[:97] + "..."
                out.write(f"\n< Cookies Received: {cookies_str}\n")

            # Content info
            if info.content_length:
                out.write(f"\n< Content Length: {info.content_length:,} bytes\n")

            # Body preview
            if info.content_preview:
                preview = info.content_preview
                if len(preview) > 200:
                    preview = preview[:197] + "..."
                # Escape newlines for cleaner output
                preview = preview.replace("\n", "\\n").replace("\r", "\\r")
                out.write(f"< Body Preview: {preview}\n")

        # TLS/impersonate info (curl backend)
        if info.impersonate:
            out.write(f"\n[TLS] Impersonate: {info.impersonate}\n")

        out.write(f"{sep}\n")
        out.flush()

    def _mask_proxy_password(self, proxy_url: str) -> str:
        """Mask password in proxy URL for display.

        Args:
            proxy_url: Proxy URL that may contain credentials.

        Returns:
            URL with password masked.
        """
        if "@" not in proxy_url:
            return proxy_url

        try:
            # Split into protocol and rest
            if "://" in proxy_url:
                protocol, rest = proxy_url.split("://", 1)
            else:
                protocol, rest = "", proxy_url

            if "@" in rest:
                creds, host = rest.rsplit("@", 1)
                if ":" in creds:
                    user, _ = creds.split(":", 1)
                    creds = f"{user}:****"
                rest = f"{creds}@{host}"

            if protocol:
                return f"{protocol}://{rest}"
            return rest
        except Exception:
            return proxy_url
