"""Optional BrowserForge integration for enhanced fingerprint generation.

BrowserForge provides more realistic, varied browser fingerprints using
a Bayesian generative network trained on real browser traffic.

Install with: pip install browserforge
Then run: python -m browserforge update

Usage:
    from http_client.fingerprint.browserforge_adapter import BrowserForgeGenerator

    # Check if available
    if BrowserForgeGenerator.is_available():
        gen = BrowserForgeGenerator()
        headers = gen.generate_headers()
        fingerprint = gen.generate_fingerprint()
"""

from __future__ import annotations

from typing import Any

# Try to import browserforge
try:
    from browserforge.headers import HeaderGenerator as BFHeaderGenerator
    from browserforge.fingerprints import FingerprintGenerator as BFFingerprintGenerator
    BROWSERFORGE_AVAILABLE = True
except ImportError:
    BROWSERFORGE_AVAILABLE = False
    BFHeaderGenerator = None
    BFFingerprintGenerator = None


class BrowserForgeGenerator:
    """Adapter for BrowserForge fingerprint generation.

    Provides enhanced, statistically realistic browser fingerprints
    as an optional upgrade from our static profiles.

    Example:
        gen = BrowserForgeGenerator(browser="chrome", os="windows")
        headers = gen.generate_headers(url="https://example.com")
    """

    def __init__(
        self,
        browser: str | list[str] | None = None,
        os: str | list[str] | None = None,
        device: str | list[str] | None = None,
        locale: str | list[str] | None = None,
        http_version: int = 2,
    ):
        """Initialize BrowserForge generator.

        Args:
            browser: Browser type(s) - "chrome", "firefox", "safari", "edge"
            os: Operating system(s) - "windows", "macos", "linux", "android", "ios"
            device: Device type(s) - "desktop", "mobile"
            locale: Locale(s) - "en-US", "en-GB", etc.
            http_version: HTTP version (1 or 2)

        Raises:
            ImportError: If browserforge is not installed.
        """
        if not BROWSERFORGE_AVAILABLE:
            raise ImportError(
                "browserforge is not installed. Install with: pip install browserforge\n"
                "Then run: python -m browserforge update"
            )

        # Only pass non-None parameters to avoid browserforge bugs
        header_kwargs = {'http_version': http_version}
        if browser is not None:
            header_kwargs['browser'] = browser
        if os is not None:
            header_kwargs['os'] = os
        if device is not None:
            header_kwargs['device'] = device
        if locale is not None:
            header_kwargs['locale'] = locale

        self._header_gen = BFHeaderGenerator(**header_kwargs)

        fingerprint_kwargs = {}
        if browser is not None:
            fingerprint_kwargs['browser'] = browser
        if os is not None:
            fingerprint_kwargs['os'] = os
        if device is not None:
            fingerprint_kwargs['device'] = device

        self._fingerprint_gen = BFFingerprintGenerator(**fingerprint_kwargs)

    @classmethod
    def is_available(cls) -> bool:
        """Check if browserforge is available."""
        return BROWSERFORGE_AVAILABLE

    def generate_headers(
        self,
        url: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Generate realistic browser headers.

        Args:
            url: Target URL (used for Sec-Fetch-* headers).
            headers: Additional headers to merge.

        Returns:
            Dict of browser headers.
        """
        # Generate base headers
        generated = self._header_gen.generate()

        # Handle both old API (object with .headers) and new API (direct dict)
        if hasattr(generated, 'headers'):
            result = dict(generated.headers)
        else:
            result = dict(generated)

        # Merge custom headers (they take precedence)
        if headers:
            result.update(headers)

        return result

    def generate_fingerprint(
        self,
        screen_width: int | None = None,
        screen_height: int | None = None,
        mock_webrtc: bool = True,
    ) -> dict[str, Any]:
        """Generate full browser fingerprint.

        Includes screen resolution, WebGL parameters, audio context,
        canvas fingerprint, and more.

        Args:
            screen_width: Constrain screen width.
            screen_height: Constrain screen height.
            mock_webrtc: Whether to mock WebRTC fingerprint.

        Returns:
            Dict containing full fingerprint data.
        """
        screen = None
        if screen_width and screen_height:
            screen = {"minWidth": screen_width, "maxWidth": screen_width,
                      "minHeight": screen_height, "maxHeight": screen_height}

        fingerprint = self._fingerprint_gen.generate(
            screen=screen,
            mock_webrtc=mock_webrtc,
        )

        return {
            "navigator": fingerprint.navigator.__dict__ if fingerprint.navigator else {},
            "screen": fingerprint.screen.__dict__ if fingerprint.screen else {},
            "headers": dict(fingerprint.headers) if fingerprint.headers else {},
            "videoCard": fingerprint.videoCard.__dict__ if fingerprint.videoCard else {},
        }

    def get_user_agent(self) -> str:
        """Generate a random realistic User-Agent string."""
        generated = self._header_gen.generate()
        # Handle both old API (object with .headers) and new API (direct dict)
        if hasattr(generated, 'headers'):
            return generated.headers.get("User-Agent", "")
        else:
            return generated.get("User-Agent", "")


class BrowserForgeHeaderGenerator:
    """Drop-in replacement for our HeaderGenerator using BrowserForge.

    Can be used as a more sophisticated alternative to the built-in
    HeaderGenerator class.
    """

    def __init__(
        self,
        browser: str | None = "chrome",
        os: str | None = None,
    ):
        """Initialize header generator.

        Args:
            browser: Browser type - "chrome", "firefox", "safari", "edge"
            os: Operating system - "windows", "macos", "linux"
        """
        if not BROWSERFORGE_AVAILABLE:
            raise ImportError("browserforge is not installed")

        self._browser = browser
        self._os = os
        # Only pass non-None parameters to avoid browserforge bugs
        kwargs = {}
        if browser is not None:
            kwargs['browser'] = browser
        if os is not None:
            kwargs['os'] = os
        self._gen = BFHeaderGenerator(**kwargs)
        self._last_referer: str | None = None

    def generate(
        self,
        url: str,
        method: str = "GET",
        custom_headers: dict[str, str] | None = None,
        include_sec_fetch: bool = True,
        referer: str | None = None,
    ) -> dict[str, str]:
        """Generate ordered headers for a request.

        Compatible with our built-in HeaderGenerator API.

        Args:
            url: Target URL.
            method: HTTP method.
            custom_headers: Additional headers to merge.
            include_sec_fetch: Whether to include Sec-Fetch-* headers.
            referer: Explicit referer URL.

        Returns:
            Dict of headers.
        """
        # Generate fresh headers
        generated = self._gen.generate()
        # Handle both old API (object with .headers) and new API (direct dict)
        if hasattr(generated, 'headers'):
            headers = dict(generated.headers)
        else:
            headers = dict(generated)

        # Handle referer
        effective_referer = referer or self._last_referer
        if effective_referer:
            headers["Referer"] = effective_referer

        # Merge custom headers
        if custom_headers:
            headers.update(custom_headers)

        # Update referer chain
        self._last_referer = url

        return headers

    def reset_referer_chain(self) -> None:
        """Reset the referer chain."""
        self._last_referer = None

    def set_referer(self, url: str) -> None:
        """Manually set the referer."""
        self._last_referer = url


def create_header_generator(
    use_browserforge: bool = False,
    browser: str = "chrome",
    **kwargs,
):
    """Factory function to create appropriate header generator.

    Args:
        use_browserforge: Whether to use BrowserForge if available.
        browser: Browser type.
        **kwargs: Additional arguments.

    Returns:
        HeaderGenerator instance (BrowserForge or built-in).
    """
    if use_browserforge and BROWSERFORGE_AVAILABLE:
        return BrowserForgeHeaderGenerator(browser=browser, **kwargs)

    # Fall back to built-in
    from .headers import HeaderGenerator
    from .profiles import get_profile

    # Map browser name to profile
    profile_map = {
        "chrome": "chrome_120",
        "firefox": "firefox_121",
        "safari": "safari_17",
        "edge": "edge_120",
    }
    profile_name = profile_map.get(browser, "chrome_120")
    return HeaderGenerator(get_profile(profile_name))
