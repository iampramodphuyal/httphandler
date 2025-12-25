"""Browser fingerprint profiles and header generation."""

from .profiles import BrowserProfile, PROFILES, get_profile
from .headers import HeaderGenerator
from .browserforge_adapter import (
    BrowserForgeGenerator,
    BrowserForgeHeaderGenerator,
    create_header_generator,
    BROWSERFORGE_AVAILABLE,
)

__all__ = [
    "BrowserProfile",
    "PROFILES",
    "get_profile",
    "HeaderGenerator",
    # BrowserForge integration (optional)
    "BrowserForgeGenerator",
    "BrowserForgeHeaderGenerator",
    "create_header_generator",
    "BROWSERFORGE_AVAILABLE",
]
