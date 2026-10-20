"""Byte-preserving lexical rendering for the managed observer plugin."""

import re
from typing import Final

from furbomek_gateway.plugin_overlay_nodes import (
    ObserverOverlayError,
    ObserverOverlayReason,
    PluginStructure,
    parse_plugin_structure,
)

_BEGIN: Final = "# BEGIN FURBOMEK MANAGED OBSERVER"
_END: Final = "# END FURBOMEK MANAGED OBSERVER"
_ITEM: Final = "- furbomek_stream"
_ROOT_KEY: Final = re.compile(r"^(?:plugins|'plugins'|\"plugins\"):")
_ROOT_HEADER: Final = re.compile(
    r"^(?:plugins|'plugins'|\"plugins\"):[ \t]*(?:#[^\r\n]*)?$"
)
_ATTRIBUTE_INDENT: Final = 2

__all__ = [
    "ObserverOverlayError",
    "ObserverOverlayReason",
    "overlay_observer",
]


def _line_text(line: str) -> str:
    return line.rstrip("\r\n")


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _root_lines(lines: list[str]) -> list[int]:
    return [
        index
        for index, line in enumerate(lines)
        if _ROOT_KEY.match(
            _line_text(line).removeprefix("\ufeff") if index == 0 else _line_text(line)
        )
    ]


def _root_end(lines: list[str], start: int) -> int:
    return next(
        (
            index
            for index in range(start + 1, len(lines))
            if _line_text(lines[index]).strip()
            and not _line_text(lines[index]).startswith((" ", "\t", "#"))
        ),
        len(lines),
    )


def _key_lines(lines: list[str], start: int, stop: int, name: str) -> list[int]:
    pattern = re.compile(rf"^  (?:{name}|'{name}'|\"{name}\"):[ \t]*(?:#[^\r\n]*)?$")
    return [
        index
        for index in range(start, stop)
        if pattern.fullmatch(_line_text(lines[index]))
    ]


def _validate_attributes(lines: list[str], start: int, stop: int) -> list[int]:
    attributes = [
        index
        for index in range(start, stop)
        if _line_text(lines[index]).strip()
        and not _line_text(lines[index]).lstrip().startswith("#")
    ]
    if any("\t" in _line_text(lines[index]) for index in attributes):
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_INDENTATION)
    if any(not lines[index].startswith("  ") for index in attributes):
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_INDENTATION)
    if (
        attributes
        and min(
            len(lines[index]) - len(lines[index].lstrip(" ")) for index in attributes
        )
        != _ATTRIBUTE_INDENT
    ):
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_INDENTATION)
    return attributes


def _enabled_end(lines: list[str], start: int, stop: int) -> tuple[int, int]:
    last_item = start
    for index in range(start + 1, stop):
        line = _line_text(lines[index])
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  ") and not line.startswith("    "):
            return index, last_item + 1
        if not line.startswith("    - "):
            raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING)
        last_item = index
    return stop, last_item + 1


def _managed_span(
    lines: list[str], enabled_start: int, enabled_stop: int
) -> tuple[int, int] | None:
    markers = [
        (index, _line_text(line))
        for index, line in enumerate(lines)
        if _BEGIN in _line_text(line) or _END in _line_text(line)
    ]
    if not markers:
        return None
    if any(line not in {f"    {_BEGIN}", f"    {_END}"} for _, line in markers):
        raise ObserverOverlayError(ObserverOverlayReason.PARTIAL_MANAGED_BLOCK)
    begins = [index for index, line in markers if line == f"    {_BEGIN}"]
    ends = [index for index, line in markers if line == f"    {_END}"]
    if (
        len(begins) != 1
        or len(ends) != 1
        or not enabled_start < begins[0] < ends[0] < enabled_stop
    ):
        raise ObserverOverlayError(ObserverOverlayReason.PARTIAL_MANAGED_BLOCK)
    content = lines[begins[0] + 1 : ends[0]]
    if len(content) != 1 or _line_text(content[0]) != f"    {_ITEM}":
        raise ObserverOverlayError(ObserverOverlayReason.PARTIAL_MANAGED_BLOCK)
    return begins[0], ends[0] + 1


def _observer_block(newline: str) -> list[str]:
    return [
        f"    {_BEGIN}{newline}",
        f"    {_ITEM}{newline}",
        f"    {_END}{newline}",
    ]


def _render_missing_root(text: str) -> str:
    newline = _newline(text)
    prefix = text if not text or text.endswith(("\n", "\r")) else text + newline
    return (
        prefix
        + "plugins:"
        + newline
        + "  enabled:"
        + newline
        + "".join(_observer_block(newline))
    )


def _render_existing(
    text: str, lines: list[str], root: int, structure: PluginStructure
) -> str:
    if not _ROOT_HEADER.fullmatch(_line_text(lines[root]).removeprefix("\ufeff")):
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING)
    stop = _root_end(lines, root)
    _ = _validate_attributes(lines, root + 1, stop)
    enabled_lines = _key_lines(lines, root + 1, stop, "enabled")
    if structure.enabled is not None and len(enabled_lines) != 1:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
    newline = _newline(text)
    if not lines[root].endswith(("\n", "\r")):
        lines[root] += newline
    if structure.enabled is None:
        return "".join(
            [
                *lines[:stop],
                f"  enabled:{newline}",
                *_observer_block(newline),
                *lines[stop:],
            ]
        )
    enabled_stop, insertion = _enabled_end(lines, enabled_lines[0], stop)
    managed = _managed_span(lines, enabled_lines[0], enabled_stop)
    if managed is not None:
        begin, end = managed
        return "".join(lines[:begin] + _observer_block(newline) + lines[end:])
    if structure.enabled_streams:
        canonical = [
            index
            for index in range(enabled_lines[0] + 1, enabled_stop)
            if _line_text(lines[index]) == f"    {_ITEM}"
        ]
        if len(canonical) != 1:
            raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
        return text
    return "".join(lines[:insertion] + _observer_block(newline) + lines[insertion:])


def overlay_observer(text: str) -> str:
    """Add or replace only the marked observer item in a block YAML document."""
    structure = parse_plugin_structure(text)
    lines = text.splitlines(keepends=True)
    roots = _root_lines(lines)
    if structure.plugins is None:
        if roots:
            raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
        return _render_missing_root(text)
    if len(roots) != 1:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
    return _render_existing(text, lines, roots[0], structure)
