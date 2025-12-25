"""Tests for browser fingerprint profiles and header generation."""

import pytest

from http_client.fingerprint import (
    BrowserProfile,
    PROFILES,
    get_profile,
    HeaderGenerator,
)
from http_client.fingerprint.profiles import (
    CHROME_120,
    CHROME_119,
    FIREFOX_121,
    SAFARI_17,
    EDGE_120,
    list_profiles,
)
from http_client.fingerprint.headers import get_minimal_headers, get_api_headers


class TestBrowserProfile:
    """Tests for BrowserProfile."""

    def test_chrome_120_profile(self):
        """Test Chrome 120 profile."""
        profile = CHROME_120

        assert profile.name == "chrome_120"
        assert profile.impersonate == "chrome120"
        assert "Chrome/120" in profile.user_agent
        assert "Windows" in profile.user_agent
        assert "Chrome" in profile.sec_ch_ua

    def test_firefox_121_profile(self):
        """Test Firefox 121 profile."""
        profile = FIREFOX_121

        assert profile.name == "firefox_121"
        assert profile.impersonate == "firefox121"
        assert "Firefox/121" in profile.user_agent
        assert profile.sec_ch_ua == ""  # Firefox doesn't have Sec-CH-UA

    def test_safari_17_profile(self):
        """Test Safari 17 profile."""
        profile = SAFARI_17

        assert profile.name == "safari_17"
        assert profile.impersonate == "safari17_0"
        assert "Safari" in profile.user_agent
        assert "Macintosh" in profile.user_agent

    def test_edge_120_profile(self):
        """Test Edge 120 profile."""
        profile = EDGE_120

        assert profile.name == "edge_120"
        assert "Edg/120" in profile.user_agent
        assert "Microsoft Edge" in profile.sec_ch_ua

    def test_get_default_headers(self):
        """Test getting default headers from profile."""
        headers = CHROME_120.get_default_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers
        assert "Sec-CH-UA" in headers  # Chrome has this

    def test_firefox_no_sec_ch_ua(self):
        """Test Firefox doesn't include Sec-CH-UA headers."""
        headers = FIREFOX_121.get_default_headers()

        assert "User-Agent" in headers
        assert "Sec-CH-UA" not in headers

    def test_header_order(self):
        """Test profile has header order defined."""
        assert len(CHROME_120.header_order) > 0
        assert "Host" in CHROME_120.header_order
        assert "User-Agent" in CHROME_120.header_order


class TestGetProfile:
    """Tests for get_profile function."""

    def test_get_chrome_profile(self):
        """Test getting Chrome profile by name."""
        profile = get_profile("chrome_120")
        assert profile == CHROME_120

    def test_get_firefox_profile(self):
        """Test getting Firefox profile by name."""
        profile = get_profile("firefox_121")
        assert profile == FIREFOX_121

    def test_get_default_profile(self):
        """Test getting default profile."""
        profile = get_profile(None)
        assert profile == CHROME_120

    def test_case_insensitive(self):
        """Test profile lookup is case insensitive."""
        assert get_profile("CHROME_120") == CHROME_120
        assert get_profile("Chrome_120") == CHROME_120

    def test_unknown_profile_raises(self):
        """Test unknown profile raises ValueError."""
        with pytest.raises(ValueError, match="Unknown profile"):
            get_profile("unknown_browser")


class TestProfilesRegistry:
    """Tests for PROFILES registry."""

    def test_all_profiles_available(self):
        """Test all expected profiles are available."""
        expected = [
            "chrome_120", "chrome_119", "chrome_118",
            "firefox_121", "firefox_120", "firefox_117",
            "safari_17", "safari_16", "safari_15",
            "edge_120", "edge_119",
        ]

        for name in expected:
            assert name in PROFILES

    def test_list_profiles(self):
        """Test listing all profile names."""
        names = list_profiles()

        assert isinstance(names, list)
        assert len(names) >= 11
        assert "chrome_120" in names
        assert names == sorted(names)  # Should be sorted


class TestHeaderGenerator:
    """Tests for HeaderGenerator."""

    def test_init_with_profile_name(self):
        """Test initialization with profile name."""
        gen = HeaderGenerator("firefox_121")
        assert gen.profile == FIREFOX_121

    def test_init_with_profile_object(self):
        """Test initialization with profile object."""
        gen = HeaderGenerator(CHROME_120)
        assert gen.profile == CHROME_120

    def test_init_default(self):
        """Test initialization with default profile."""
        gen = HeaderGenerator()
        assert gen.profile == CHROME_120

    def test_generate_basic(self):
        """Test basic header generation."""
        gen = HeaderGenerator("chrome_120")
        headers = gen.generate("https://example.com")

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Chrome/120" in headers["User-Agent"]

    def test_generate_with_sec_fetch(self):
        """Test header generation with Sec-Fetch headers."""
        gen = HeaderGenerator("chrome_120")
        headers = gen.generate("https://example.com", include_sec_fetch=True)

        assert "Sec-Fetch-Site" in headers
        assert "Sec-Fetch-Mode" in headers
        assert "Sec-Fetch-Dest" in headers

    def test_generate_without_sec_fetch(self):
        """Test header generation without Sec-Fetch headers."""
        gen = HeaderGenerator("chrome_120")
        headers = gen.generate("https://example.com", include_sec_fetch=False)

        assert "Sec-Fetch-Site" not in headers
        assert "Sec-Fetch-Mode" not in headers

    def test_custom_headers_merged(self):
        """Test custom headers are merged."""
        gen = HeaderGenerator("chrome_120")
        headers = gen.generate(
            "https://example.com",
            custom_headers={"X-Custom": "value", "Accept": "application/json"},
        )

        assert headers["X-Custom"] == "value"
        assert headers["Accept"] == "application/json"  # Overrides profile default

    def test_referer_chain(self):
        """Test referer chain building."""
        gen = HeaderGenerator("chrome_120")

        # First request - no referer
        headers1 = gen.generate("https://example.com")
        assert "Referer" not in headers1

        # Second request - has referer from first
        headers2 = gen.generate("https://example.com/page2")
        assert headers2.get("Referer") == "https://example.com"

        # Third request - has referer from second
        headers3 = gen.generate("https://example.com/page3")
        assert headers3.get("Referer") == "https://example.com/page2"

    def test_explicit_referer(self):
        """Test explicit referer override."""
        gen = HeaderGenerator("chrome_120")
        gen.generate("https://first.com")  # Set auto referer

        headers = gen.generate(
            "https://second.com",
            referer="https://explicit.com",
        )

        assert headers["Referer"] == "https://explicit.com"

    def test_reset_referer_chain(self):
        """Test resetting referer chain."""
        gen = HeaderGenerator("chrome_120")
        gen.generate("https://example.com")

        gen.reset_referer_chain()

        headers = gen.generate("https://other.com")
        assert "Referer" not in headers

    def test_set_referer(self):
        """Test manually setting referer."""
        gen = HeaderGenerator("chrome_120")
        gen.set_referer("https://manual.com")

        headers = gen.generate("https://example.com")
        assert headers.get("Referer") == "https://manual.com"

    def test_sec_fetch_site_none(self):
        """Test Sec-Fetch-Site is 'none' for first request."""
        gen = HeaderGenerator("chrome_120")
        headers = gen.generate("https://example.com")

        assert headers["Sec-Fetch-Site"] == "none"

    def test_sec_fetch_site_same_origin(self):
        """Test Sec-Fetch-Site is 'same-origin' for same domain."""
        gen = HeaderGenerator("chrome_120")
        gen.generate("https://example.com/page1")
        headers = gen.generate("https://example.com/page2")

        assert headers["Sec-Fetch-Site"] == "same-origin"

    def test_sec_fetch_site_cross_site(self):
        """Test Sec-Fetch-Site is 'cross-site' for different domain."""
        gen = HeaderGenerator("chrome_120")
        gen.generate("https://example.com")
        headers = gen.generate("https://other.com")

        assert headers["Sec-Fetch-Site"] == "cross-site"


class TestHelperFunctions:
    """Tests for helper header functions."""

    def test_minimal_headers(self):
        """Test minimal headers for speed mode."""
        headers = get_minimal_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert len(headers) < 5  # Should be minimal

    def test_api_headers(self):
        """Test API headers for JSON requests."""
        headers = get_api_headers()

        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
