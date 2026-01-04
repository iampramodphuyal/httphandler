"""Header generation and ordering for browser fingerprinting."""

from __future__ import annotations

from collections import OrderedDict
from typing import Literal
from urllib.parse import urlparse

from .profiles import BrowserProfile, get_profile


class HeaderGenerator:
    """Generate and order headers to match browser fingerprints.

    Handles:
    - Default header generation based on browser profile
    - Header ordering to match real browser behavior
    - Sec-Fetch-* header generation
    - Referer header management
    """

    def __init__(self, profile: BrowserProfile | str | None = None):
        """Initialize header generator.

        Args:
            profile: BrowserProfile instance or profile name string.
        """
        if profile is None or isinstance(profile, str):
            self._profile = get_profile(profile)
        else:
            self._profile = profile

        self._last_referer: str | None = None

    @property
    def profile(self) -> BrowserProfile:
        """Get current browser profile."""
        return self._profile

    def generate(
        self,
        url: str,
        method: str = "GET",
        custom_headers: dict[str, str] | None = None,
        include_sec_fetch: bool = True,
        referer: str | None = None,
    ) -> dict[str, str]:
        """Generate ordered headers for a request.

        Args:
            url: Target URL.
            method: HTTP method.
            custom_headers: Additional headers to merge.
            include_sec_fetch: Whether to include Sec-Fetch-* headers.
            referer: Explicit referer URL (overrides automatic tracking).

        Returns:
            Ordered dict of headers.
        """
        # Start with profile defaults
        headers = self._profile.get_default_headers()

        # Add Sec-Fetch headers if enabled
        if include_sec_fetch:
            sec_fetch = self._generate_sec_fetch(url, method)
            headers.update(sec_fetch)

        # Handle referer
        effective_referer = referer or self._last_referer
        if effective_referer:
            headers["Referer"] = effective_referer

        # Merge custom headers (they take precedence)
        if custom_headers:
            headers.update(custom_headers)

        # Order headers according to profile
        ordered = self._order_headers(headers)

        # Update last referer for chain building
        self._last_referer = url

        return ordered

    def _is_same_site(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are same-site (share registrable domain).

        Uses a simple heuristic that works for most cases without requiring
        a full public suffix list. Handles common multi-level TLDs.

        Args:
            domain1: First domain (netloc).
            domain2: Second domain (netloc).

        Returns:
            True if domains are same-site.
        """
        if not domain1 or not domain2:
            return False

        # Remove port if present
        domain1 = domain1.split(":")[0].lower()
        domain2 = domain2.split(":")[0].lower()

        # Exact match is same-origin, not just same-site, but counts
        if domain1 == domain2:
            return True

        # Known multi-level TLDs (common ones)
        multi_level_tlds = {
            "co.uk", "org.uk", "gov.uk", "ac.uk",
            "com.au", "org.au", "gov.au", "edu.au",
            "co.nz", "org.nz", "gov.nz",
            "co.jp", "or.jp", "ne.jp",
            "com.br", "org.br", "gov.br",
            "co.in", "org.in", "gov.in",
            "com.cn", "org.cn", "gov.cn",
        }

        def get_registrable_domain(domain: str) -> str:
            """Extract registrable domain (eTLD+1)."""
            parts = domain.split(".")
            if len(parts) < 2:
                return domain

            # Check for multi-level TLD
            for tld in multi_level_tlds:
                if domain.endswith("." + tld) or domain == tld:
                    tld_parts = tld.split(".")
                    if len(parts) > len(tld_parts):
                        return ".".join(parts[-(len(tld_parts) + 1):])
                    return domain

            # Default: take last two parts
            return ".".join(parts[-2:])

        return get_registrable_domain(domain1) == get_registrable_domain(domain2)

    def _generate_sec_fetch(self, url: str, method: str) -> dict[str, str]:
        """Generate Sec-Fetch-* headers.

        Args:
            url: Target URL.
            method: HTTP method.

        Returns:
            Dict of Sec-Fetch headers.
        """
        try:
            parsed = urlparse(url)
        except Exception:
            # If URL parsing fails, use safe defaults
            return {
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
            }

        # Determine fetch site
        sec_fetch_site = "none"
        if self._last_referer:
            try:
                last_parsed = urlparse(self._last_referer)
                if last_parsed.netloc and parsed.netloc:
                    if last_parsed.netloc == parsed.netloc:
                        sec_fetch_site = "same-origin"
                    elif self._is_same_site(last_parsed.netloc, parsed.netloc):
                        sec_fetch_site = "same-site"
                    else:
                        sec_fetch_site = "cross-site"
                else:
                    sec_fetch_site = "cross-site"
            except Exception:
                sec_fetch_site = "cross-site"

        # Determine fetch mode based on request type
        sec_fetch_mode = "navigate"

        # Determine fetch dest
        sec_fetch_dest = "document"

        headers = {
            "Sec-Fetch-Site": sec_fetch_site,
            "Sec-Fetch-Mode": sec_fetch_mode,
            "Sec-Fetch-Dest": sec_fetch_dest,
        }

        # Add Sec-Fetch-User for navigation requests
        if method.upper() == "GET":
            headers["Sec-Fetch-User"] = "?1"

        return headers

    def _order_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Order headers according to browser profile.

        Args:
            headers: Unordered headers.

        Returns:
            OrderedDict with headers in profile-specified order.
        """
        ordered: dict[str, str] = {}
        remaining = dict(headers)

        # First, add headers in profile order
        for header_name in self._profile.header_order:
            # Case-insensitive lookup
            for key, value in list(remaining.items()):
                if key.lower() == header_name.lower():
                    ordered[key] = value
                    del remaining[key]
                    break

        # Then add any remaining headers not in the order list
        ordered.update(remaining)

        return ordered

    def reset_referer_chain(self) -> None:
        """Reset the referer chain (start fresh navigation)."""
        self._last_referer = None

    def set_referer(self, url: str) -> None:
        """Manually set the referer for the next request.

        Args:
            url: Referer URL to set.
        """
        self._last_referer = url


# Pre-built header sets for common scenarios
MINIMAL_HEADERS = {
    "User-Agent": "python-httpx/0.27.0",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

API_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Content-Type": "application/json",
}


def get_minimal_headers() -> dict[str, str]:
    """Get minimal headers for speed mode."""
    return dict(MINIMAL_HEADERS)


def get_api_headers() -> dict[str, str]:
    """Get headers for JSON API requests."""
    return dict(API_HEADERS)
