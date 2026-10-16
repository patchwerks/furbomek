import pytest

from furbomek_gateway.config_overlay import (
    ConfigOverlayError,
    McpServerEntry,
    overlay_mcp_server,
)


def entry() -> McpServerEntry:
    return McpServerEntry(command="uv", args=("run", "furbomek-gateway"))


def test_overlay_preserves_existing_settings_and_servers() -> None:
    prefix = "# existing settings\nmodel:\n  default: existing-model\n"
    suffix = (
        "  other:\n    command: existing-command\n"
        "# keep footer\nagent:\n  max_turns: 7\n"
    )
    original = prefix + "mcp_servers:\n" + suffix

    result = overlay_mcp_server(original, entry())

    assert result.startswith(prefix + "mcp_servers:\n")
    assert result.endswith(suffix)
    assert result.count("  furbomek:") == 1
    assert result.count("mcp_servers:") == 1


def test_overlay_is_idempotent_and_updates_only_owned_entry() -> None:
    original = "mcp_servers:\n    other:\n      command: existing\n"
    initial = overlay_mcp_server(original, entry())

    unchanged = overlay_mcp_server(initial, entry())
    changed = overlay_mcp_server(
        initial, McpServerEntry(command="uv", args=("run", "new-entrypoint"))
    )

    assert unchanged == initial
    assert changed.endswith("    other:\n      command: existing\n")
    assert changed.count("    furbomek:") == 1
    assert '"new-entrypoint"' in changed
    assert '"furbomek-gateway"' not in changed


@pytest.mark.parametrize(
    "original",
    [
        "mcp_servers: {}\n",
        "mcp_servers:\n  other: {}\nmcp_servers:\n  another: {}\n",
        "mcp_servers:\n  furbomek:\n    command: user-owned\n",
        "mcp_servers:\n  'furbomek': {command: user-owned}\n",
        "mcp_servers:\n  # BEGIN FURBOMEK MANAGED MCP\n",
        "mcp_servers :\n  other: {}\n",
        "mcp_servers:\n  furbomek : {command: user-owned}\n",
        '"mcp_\\u0073ervers":\n  other: {}\n',
        'mcp_servers:\n  "furbom\\u0065k": {command: user-owned}\n',
        "? mcp_servers\n:\n  other: {}\n",
        "base: &base\n  mcp_servers:\n    other: {}\n<<: *base\n",
    ],
)
def test_overlay_refuses_ambiguous_or_unmanaged_configuration(original: str) -> None:
    with pytest.raises(ConfigOverlayError):
        _ = overlay_mcp_server(original, entry())


def test_overlay_creates_mapping_without_changing_existing_content() -> None:
    original = "# retained\nmodel: existing"

    result = overlay_mcp_server(original, entry())

    assert result.startswith(original + "\nmcp_servers:\n")
    assert result.count("  furbomek:") == 1


def test_overlay_preserves_bom_quoted_key_and_crlf() -> None:
    original = '\ufeff"mcp_servers":\r\n  other: {}\r\n'

    result = overlay_mcp_server(original, entry())

    assert result.startswith('\ufeff"mcp_servers":\r\n')
    assert result.endswith("  other: {}\r\n")
    assert "\n" not in result.replace("\r\n", "")


def test_overlay_can_disable_only_the_owned_server_for_rollback() -> None:
    original = "mcp_servers:\n  other: {command: retained}\n"

    result = overlay_mcp_server(
        original, McpServerEntry(command="uv", args=("run",), enabled=False)
    )

    assert '"enabled":false' in result
    assert result.endswith("  other: {command: retained}\n")
