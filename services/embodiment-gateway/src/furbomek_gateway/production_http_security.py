"""Exact trusted origin policy shared by private owner HTTP request methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from email.message import Message


def trusted_origin(
    headers: Message[str, str], authority: str, origin: str, method: str
) -> bool:
    """Custom GET header requires same-origin browser fetch; POST requires Origin."""
    checks = (
        headers.get_all("Host") == [authority],
        (
            headers.get_all("Origin") == [origin]
            or (
                method == "GET"
                and headers.get("Origin") is None
                and headers.get("X-Owner-Request") == "1"
            )
        ),
        headers.get("Sec-Fetch-Site", "same-origin") == "same-origin",
        headers.get("Sec-Fetch-Mode", "cors") != "navigate",
        headers.get("Sec-Fetch-Dest", "empty") == "empty",
        headers.get("Transfer-Encoding") is None,
    )
    return all(checks)
