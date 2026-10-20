from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin"))

from furbomek_stream.projection import JsonObject, JsonValue, project_tool, public_host

SECRET = "hunter2-sk-live-XYZ"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.example.com/path?token=abc#frag", "public page"),
        ("http://news.ycombinator.com/item?id=1", "public page"),
        ("https://user:pass@github.com/x", "public page"),
        ("http://127.0.0.1:8080/admin", "private page"),
        ("http://192.168.1.4/", "private page"),
        ("http://localhost:3000", "private page"),
        ("https://example-host.example-tailnet.ts.net/", "private page"),
        ("file:///home/lock/.hermes/.env", "local page"),
        ("javascript:alert(1)", "—"),
        (12, "—"),
    ],
)
def test_public_host_reduces_urls_to_safe_hostnames(url: JsonValue, expected: str) -> None:
    assert public_host(url) == expected


def test_typed_text_is_never_projected() -> None:
    cases: tuple[tuple[str, JsonObject], ...] = (
        ("browser_type", {"ref": "@e3", "text": SECRET}),
        ("computer_use", {"action": "type", "text": SECRET, "app": "Firefox"}),
        ("computer_use", {"action": "set_value", "value": SECRET}),
        ("web_search", {"query": SECRET}),
        ("terminal", {"command": f"echo {SECRET}"}),
        ("browser_exec", {"code": f"fetch('{SECRET}')"}),
        ("write_file", {"path": "/tmp/x", "content": SECRET}),
        ("unknown_tool", {"anything": SECRET}),
    )
    for tool, args in cases:
        projected = project_tool(tool, args)
        assert SECRET not in json.dumps([projected.category, projected.action, projected.detail])


def test_sensitive_destinations_trigger_the_privacy_shutter() -> None:
    assert project_tool("browser_vault", {"action": "fill"}).shutter
    assert project_tool("browser_navigate", {"url": "https://accounts.google.com/signin"}).shutter
    assert project_tool("browser_navigate", {"url": "http://127.0.0.1:3000"}).shutter
    assert not project_tool("browser_navigate", {"url": "https://example.com"}).shutter
    assert project_tool("browser_navigate", {"url": "https://example.com"}).privacy_release


def test_key_names_are_allowlisted() -> None:
    assert project_tool("browser_press", {"key": "Enter"}).detail == "Enter"
    assert project_tool("computer_use", {"action": "key", "keys": ["ctrl+l"]}).detail == "key"
    assert project_tool("computer_use", {"action": "key", "keys": ["hunter2"]}).detail == "key"


def test_computer_use_projection_hides_app_and_coordinates() -> None:
    projected = project_tool("computer_use", {"action": "click", "coordinate": [133, 421], "app": "Firefox"})
    assert projected.category == "COMPUTER"
    assert "Firefox" not in projected.detail
    assert "133" not in projected.detail
    assert project_tool("computer_use", {"action": "focus_app", "app": "rm -rf /; x"}).detail == "app"


@pytest.mark.parametrize(
    "action",
    [
        "capture",
        "click",
        "double_click",
        "right_click",
        "middle_click",
        "type",
        "set_value",
        "key",
        "scroll",
        "drag",
        "focus_app",
        "list_apps",
        "list_windows",
        "wait",
    ],
)
def test_app_secret_canary_never_enters_public_projection(action: str) -> None:
    projected = project_tool("computer_use", {"action": action, "app": SECRET})
    assert SECRET not in json.dumps([projected.category, projected.action, projected.detail])


def test_screen_capable_browser_tools_are_shuttered_without_certifying_pixels() -> None:
    for tool in ("browser_exec", "browser_cdp", "browser_dialog", "browser_click", "browser_back", "browser_snapshot"):
        assert project_tool(tool, {}).shutter


def test_unknown_tools_collapse_to_a_generic_action() -> None:
    projected = project_tool("mcp_github_create_issue", {"title": SECRET})
    assert (projected.category, projected.action, projected.detail) == ("AGENT", "using a tool", "")
