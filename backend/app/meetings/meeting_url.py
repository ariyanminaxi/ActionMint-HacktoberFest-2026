"""The one Google Meet URL validator (Amendment C.24).

Rules: https only, hostname exactly `meet.google.com`, no credentials, no port, and a path that
is exactly one Meet code `^[a-z]{3}-[a-z]{4}-[a-z]{3}$`. Query strings and fragments are stripped
before the URL is stored. Anything else is rejected, including look-alike hosts such as
`meet.google.com.evil.com` and percent-encoded tricks.

The raw string is never pattern-matched: it is parsed, then the parsed host is compared exactly.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

MEET_HOST = "meet.google.com"
MEET_CODE = re.compile(r"^[a-z]{3}-[a-z]{4}-[a-z]{3}$")
UNSUPPORTED_MESSAGE = "Only Google Meet links (meet.google.com) are supported."
UNSUPPORTED_CODE = "unsupported_platform"


class UnsupportedPlatform(ValueError):
    """Raised when a URL is not an accepted Google Meet link."""

    code = UNSUPPORTED_CODE

    def __init__(self, message: str = UNSUPPORTED_MESSAGE) -> None:
        super().__init__(message)


def normalize_meet_url(raw: str) -> str:
    """Return the canonical `https://meet.google.com/<code>` or raise UnsupportedPlatform."""
    if not raw or not raw.isascii():
        raise UnsupportedPlatform()
    try:
        parts = urlsplit(raw.strip())
        port = parts.port
    except ValueError:
        raise UnsupportedPlatform() from None
    if parts.scheme != "https":
        raise UnsupportedPlatform()
    if parts.username or parts.password or port is not None:
        raise UnsupportedPlatform()
    if (parts.hostname or "") != MEET_HOST:
        raise UnsupportedPlatform()
    code = parts.path.lstrip("/")
    if not MEET_CODE.fullmatch(code):
        raise UnsupportedPlatform()
    # Rebuild from the validated parts: drops query, fragment and any trailing slash.
    return f"https://{MEET_HOST}/{code}"
