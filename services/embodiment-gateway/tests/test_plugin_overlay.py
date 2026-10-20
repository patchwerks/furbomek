import pytest
from typer.testing import CliRunner

from furbomek_gateway.cli import app
from furbomek_gateway.plugin_overlay import (
    ObserverOverlayError,
    ObserverOverlayReason,
    overlay_observer,
)

_BEGIN = "    # BEGIN FURBOMEK MANAGED OBSERVER\n"
_ITEM = "    - furbomek_stream\n"
_END = "    # END FURBOMEK MANAGED OBSERVER\n"
_BLOCK = _BEGIN + _ITEM + _END


def test_overlay_preserves_unowned_bytes_and_provider_secret() -> None:
    original = (
        "# keep this comment\n"
        "provider:\n"
        "  api_key: provider-secret-canary\n"
        "  options: {region: eu, token: keep-this-byte-order}\n"
        "plugins:\n"
        "  enabled:\n"
        "    - moshi-hooks\n"
        "  disabled:\n"
        "    - acpx-opencode\n"
        "# keep this footer\n"
    )

    result = overlay_observer(original)

    expected_prefix = (
        "# keep this comment\nprovider:\n  api_key: provider-secret-canary\n"
    )
    expected_prefix += "  options: {region: eu, token: keep-this-byte-order}\n"
    expected_prefix += "plugins:\n  enabled:\n    - moshi-hooks\n"
    expected_suffix = "  disabled:\n    - acpx-opencode\n# keep this footer\n"
    assert result == expected_prefix + _BLOCK + expected_suffix


def test_overlay_preserves_quoted_provider_asterisk_text() -> None:
    original = (
        "provider:\n"
        "  prompt: 'use *model as context'\n"
        "plugins:\n"
        "  enabled:\n"
        "    - moshi-hooks\n"
    )

    result = overlay_observer(original)

    assert result.startswith("provider:\n  prompt: 'use *model as context'\n")
    assert result.endswith("    - moshi-hooks\n" + _BLOCK)


def test_overlay_is_idempotent() -> None:
    original = "plugins:\n  enabled:\n    - moshi-hooks\n"

    first = overlay_observer(original)

    assert overlay_observer(first) == first


def test_overlay_adds_missing_root_at_end_without_rewriting_existing_bytes() -> None:
    original = "# retained\nmodel: existing"

    result = overlay_observer(original)

    assert result == original + "\nplugins:\n  enabled:\n" + _BLOCK


def test_overlay_adds_missing_enabled_before_next_root_key_and_keeps_disabled() -> None:
    original = (
        "plugins:\n"
        "  disabled:\n"
        "    - acpx-opencode\n"
        "provider: {token: provider-secret-canary}\n"
    )

    result = overlay_observer(original)

    expected_prefix = "plugins:\n  disabled:\n    - acpx-opencode\n  enabled:\n"
    expected_suffix = "provider: {token: provider-secret-canary}\n"
    assert result == expected_prefix + _BLOCK + expected_suffix


def test_overlay_adds_enabled_to_empty_block_mapping() -> None:
    original = "plugins:\n  disabled: []\n"

    result = overlay_observer(original)

    assert result == "plugins:\n  disabled: []\n  enabled:\n" + _BLOCK


def test_overlay_repairs_missing_newline_before_existing_root_children() -> None:
    original = "plugins:"

    assert overlay_observer(original) == "plugins:\n  enabled:\n" + _BLOCK


def test_overlay_leaves_unmanaged_existing_item_unchanged() -> None:
    original = "plugins:\n  enabled:\n    - furbomek_stream\n"

    assert overlay_observer(original) == original


def test_overlay_refuses_explicitly_disabled_observer() -> None:
    original = "plugins:\n  enabled:\n    - moshi-hooks\n"
    original += "  disabled:\n    - furbomek_stream\n"

    with pytest.raises(ObserverOverlayError) as error:
        _ = overlay_observer(original)

    assert error.value.reason is ObserverOverlayReason.DISABLED


@pytest.mark.parametrize(
    "original",
    [
        "plugins:\n  enabled:\n    - one\nplugins:\n  enabled:\n    - two\n",
        "plugins:\n  enabled:\n    - one\n  enabled:\n    - two\n",
        '"plugins":\n  "enabled":\n    - "furbomek_stream"\n',
        'plugins:\n  "en\\u0061bled":\n    - one\n',
        '"pl\\u0075gins":\n  enabled:\n    - one\n',
        'plugins:\n  enabled:\n    - "furbomek_\\u0073tream"\n',
    ],
)
def test_overlay_refuses_duplicate_or_escaped_target_names(original: str) -> None:
    with pytest.raises(ObserverOverlayError):
        _ = overlay_observer(original)


@pytest.mark.parametrize(
    "original",
    [
        "base: &base\n  enabled:\n    - one\nplugins:\n  <<: *base\n",
        "base: &enabled\n  - one\nplugins:\n  enabled: *enabled\n",
        "plugins:\n  enabled:\n    - one\n  <<: {enabled: [two]}\n",
    ],
)
def test_overlay_refuses_alias_and_merge_target_structures(original: str) -> None:
    with pytest.raises(ObserverOverlayError):
        _ = overlay_observer(original)


@pytest.mark.parametrize(
    "original",
    [
        "plugins: {enabled: [moshi-hooks]}\n",
        "plugins:\n  enabled: [moshi-hooks]\n",
        "{provider: {token: provider-secret-canary}}\n",
        "plugins:\n  enabled:\n    - {name: moshi-hooks}\n",
    ],
)
def test_overlay_refuses_flow_or_unsupported_target_structures(original: str) -> None:
    with pytest.raises(ObserverOverlayError):
        _ = overlay_observer(original)


@pytest.mark.parametrize(
    "original",
    [
        "plugins:\n  enabled:\n    # BEGIN FURBOMEK MANAGED OBSERVER\n",
        (
            "plugins:\n  enabled:\n"
            "    # BEGIN FURBOMEK MANAGED OBSERVER\n"
            "    - furbomek_stream\n"
        ),
        (
            "plugins:\n  enabled:\n"
            "  # BEGIN FURBOMEK MANAGED OBSERVER\n"
            "    - furbomek_stream\n"
            "  # END FURBOMEK MANAGED OBSERVER\n"
        ),
        (
            "plugins:\n  enabled:\n"
            "    # BEGIN FURBOMEK MANAGED OBSERVER\n"
            "    - other\n"
            "    # END FURBOMEK MANAGED OBSERVER\n"
        ),
    ],
)
def test_overlay_refuses_partial_or_malformed_markers(original: str) -> None:
    with pytest.raises(ObserverOverlayError):
        _ = overlay_observer(original)


def test_overlay_preserves_crlf() -> None:
    original = "plugins:\r\n  enabled:\r\n    - moshi-hooks\r\n"

    result = overlay_observer(original)

    assert result == "plugins:\r\n  enabled:\r\n    - moshi-hooks\r\n" + _BLOCK.replace(
        "\n", "\r\n"
    )
    assert "\n" not in result.replace("\r\n", "")


def test_cli_transforms_piped_input() -> None:
    original = "plugins:\n  enabled:\n    - moshi-hooks\n"

    result = CliRunner().invoke(app, ["overlay-observer"], input=original)

    assert result.exit_code == 0
    assert result.stdout == original[: -len("\n")] + "\n" + _BLOCK


def test_cli_returns_code_two_without_error_content() -> None:
    result = CliRunner().invoke(
        app,
        ["overlay-observer"],
        input="plugins: {enabled: [moshi-hooks]}\n",
    )

    assert result.exit_code == 2
    assert result.stdout == ""
