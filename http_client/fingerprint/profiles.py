"""Browser fingerprint profiles for TLS impersonation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class BrowserProfile:
    """Browser fingerprint profile for curl_cffi impersonation.

    Attributes:
        name: Profile identifier (e.g., "chrome_120").
        impersonate: curl_cffi impersonate string.
        user_agent: User-Agent header value.
        header_order: List defining header transmission order.
        accept: Accept header value.
        accept_language: Accept-Language header value.
        accept_encoding: Accept-Encoding header value.
        sec_ch_ua: Sec-CH-UA header value.
        sec_ch_ua_mobile: Sec-CH-UA-Mobile header value.
        sec_ch_ua_platform: Sec-CH-UA-Platform header value.
    """

    name: str
    impersonate: str
    user_agent: str
    header_order: tuple[str, ...]
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    accept_language: str = "en-US,en;q=0.9"
    accept_encoding: str = "gzip, deflate, br"
    sec_ch_ua: str = ""
    sec_ch_ua_mobile: str = "?0"
    sec_ch_ua_platform: str = ""

    def get_default_headers(self) -> dict[str, str]:
        """Get default headers for this profile."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": self.accept,
            "Accept-Language": self.accept_language,
            "Accept-Encoding": self.accept_encoding,
        }

        # Add Chrome-specific headers
        if self.sec_ch_ua:
            headers["Sec-CH-UA"] = self.sec_ch_ua
            headers["Sec-CH-UA-Mobile"] = self.sec_ch_ua_mobile
            headers["Sec-CH-UA-Platform"] = self.sec_ch_ua_platform

        return headers


# Chrome profiles
CHROME_120 = BrowserProfile(
    name="chrome_120",
    impersonate="chrome120",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    header_order=(
        "Host",
        "Connection",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "Upgrade-Insecure-Requests",
        "User-Agent",
        "Accept",
        "Sec-Fetch-Site",
        "Sec-Fetch-Mode",
        "Sec-Fetch-User",
        "Sec-Fetch-Dest",
        "Referer",
        "Accept-Encoding",
        "Accept-Language",
        "Cookie",
    ),
    sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    sec_ch_ua_mobile="?0",
    sec_ch_ua_platform='"Windows"',
)

CHROME_119 = BrowserProfile(
    name="chrome_119",
    impersonate="chrome119",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    header_order=(
        "Host",
        "Connection",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "Upgrade-Insecure-Requests",
        "User-Agent",
        "Accept",
        "Sec-Fetch-Site",
        "Sec-Fetch-Mode",
        "Sec-Fetch-User",
        "Sec-Fetch-Dest",
        "Referer",
        "Accept-Encoding",
        "Accept-Language",
        "Cookie",
    ),
    sec_ch_ua='"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    sec_ch_ua_mobile="?0",
    sec_ch_ua_platform='"Windows"',
)

CHROME_118 = BrowserProfile(
    name="chrome_118",
    impersonate="chrome118",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    header_order=(
        "Host",
        "Connection",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "Upgrade-Insecure-Requests",
        "User-Agent",
        "Accept",
        "Sec-Fetch-Site",
        "Sec-Fetch-Mode",
        "Sec-Fetch-User",
        "Sec-Fetch-Dest",
        "Referer",
        "Accept-Encoding",
        "Accept-Language",
        "Cookie",
    ),
    sec_ch_ua='"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
    sec_ch_ua_mobile="?0",
    sec_ch_ua_platform='"Windows"',
)

# Firefox profiles
FIREFOX_121 = BrowserProfile(
    name="firefox_121",
    impersonate="firefox121",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    header_order=(
        "Host",
        "User-Agent",
        "Accept",
        "Accept-Language",
        "Accept-Encoding",
        "Connection",
        "Referer",
        "Cookie",
        "Upgrade-Insecure-Requests",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "Sec-Fetch-User",
    ),
    accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
)

FIREFOX_120 = BrowserProfile(
    name="firefox_120",
    impersonate="firefox120",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    header_order=(
        "Host",
        "User-Agent",
        "Accept",
        "Accept-Language",
        "Accept-Encoding",
        "Connection",
        "Referer",
        "Cookie",
        "Upgrade-Insecure-Requests",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "Sec-Fetch-User",
    ),
    accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
)

FIREFOX_117 = BrowserProfile(
    name="firefox_117",
    impersonate="firefox117",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    header_order=(
        "Host",
        "User-Agent",
        "Accept",
        "Accept-Language",
        "Accept-Encoding",
        "Connection",
        "Referer",
        "Cookie",
        "Upgrade-Insecure-Requests",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "Sec-Fetch-User",
    ),
    accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
)

# Safari profiles
SAFARI_17 = BrowserProfile(
    name="safari_17",
    impersonate="safari17_0",
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    header_order=(
        "Host",
        "Accept",
        "Sec-Fetch-Site",
        "Accept-Language",
        "Sec-Fetch-Mode",
        "Accept-Encoding",
        "Sec-Fetch-Dest",
        "User-Agent",
        "Referer",
        "Connection",
        "Cookie",
    ),
    accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    accept_language="en-US,en;q=0.9",
)

SAFARI_16 = BrowserProfile(
    name="safari_16",
    impersonate="safari16_0",
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    header_order=(
        "Host",
        "Accept",
        "Sec-Fetch-Site",
        "Accept-Language",
        "Sec-Fetch-Mode",
        "Accept-Encoding",
        "Sec-Fetch-Dest",
        "User-Agent",
        "Referer",
        "Connection",
        "Cookie",
    ),
    accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    accept_language="en-US,en;q=0.9",
)

SAFARI_15 = BrowserProfile(
    name="safari_15",
    impersonate="safari15_5",
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    header_order=(
        "Host",
        "Accept",
        "Sec-Fetch-Site",
        "Accept-Language",
        "Sec-Fetch-Mode",
        "Accept-Encoding",
        "Sec-Fetch-Dest",
        "User-Agent",
        "Referer",
        "Connection",
        "Cookie",
    ),
    accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    accept_language="en-US,en;q=0.9",
)

# Edge profiles
EDGE_120 = BrowserProfile(
    name="edge_120",
    impersonate="edge120",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    header_order=(
        "Host",
        "Connection",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "Upgrade-Insecure-Requests",
        "User-Agent",
        "Accept",
        "Sec-Fetch-Site",
        "Sec-Fetch-Mode",
        "Sec-Fetch-User",
        "Sec-Fetch-Dest",
        "Referer",
        "Accept-Encoding",
        "Accept-Language",
        "Cookie",
    ),
    sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
    sec_ch_ua_mobile="?0",
    sec_ch_ua_platform='"Windows"',
)

EDGE_119 = BrowserProfile(
    name="edge_119",
    impersonate="edge119",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    header_order=(
        "Host",
        "Connection",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "Upgrade-Insecure-Requests",
        "User-Agent",
        "Accept",
        "Sec-Fetch-Site",
        "Sec-Fetch-Mode",
        "Sec-Fetch-User",
        "Sec-Fetch-Dest",
        "Referer",
        "Accept-Encoding",
        "Accept-Language",
        "Cookie",
    ),
    sec_ch_ua='"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    sec_ch_ua_mobile="?0",
    sec_ch_ua_platform='"Windows"',
)


# Profile registry
PROFILES: dict[str, BrowserProfile] = {
    # Chrome
    "chrome_120": CHROME_120,
    "chrome_119": CHROME_119,
    "chrome_118": CHROME_118,
    # Firefox
    "firefox_121": FIREFOX_121,
    "firefox_120": FIREFOX_120,
    "firefox_117": FIREFOX_117,
    # Safari
    "safari_17": SAFARI_17,
    "safari_16": SAFARI_16,
    "safari_15": SAFARI_15,
    # Edge
    "edge_120": EDGE_120,
    "edge_119": EDGE_119,
}

# Default profile
DEFAULT_PROFILE = "chrome_120"


def get_profile(name: str | None = None) -> BrowserProfile:
    """Get a browser profile by name.

    Args:
        name: Profile name. If None, returns default profile.

    Returns:
        BrowserProfile instance.

    Raises:
        ValueError: If profile name not found.
    """
    if name is None:
        name = DEFAULT_PROFILE

    name = name.lower()
    if name not in PROFILES:
        available = ", ".join(sorted(PROFILES.keys()))
        raise ValueError(f"Unknown profile '{name}'. Available: {available}")

    return PROFILES[name]


def list_profiles() -> list[str]:
    """Get list of available profile names."""
    return sorted(PROFILES.keys())
