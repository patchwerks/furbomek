"""Shared short-lived semantic request time fence."""

import time
from typing import Final

REQUEST_AGE_MS: Final = 5000
CLOCK_SKEW_MS: Final = 1000


def unix_ms() -> int:
    """Return epoch milliseconds for bounded semantic messages."""
    return time.time_ns() // 1_000_000
