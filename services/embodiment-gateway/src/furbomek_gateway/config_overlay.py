"""Comment-preserving, fail-closed enrollment of one owned Hermes MCP entry."""

import re
from enum import StrEnum
from typing import Annotated, ClassVar, Final, Literal, override

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from yaml import SafeLoader, YAMLError
from yaml.nodes import MappingNode, Node, ScalarNode

_BEGIN: Final = "# BEGIN FURBOMEK MANAGED MCP"
_END: Final = "# END FURBOMEK MANAGED MCP"
_ROOT_KEY: Final = re.compile(r"^(?:mcp_servers|'mcp_servers'|\"mcp_servers\"):")
_BLOCK_HEADER: Final = re.compile(
    r"^(?:mcp_servers|'mcp_servers'|\"mcp_servers\"):[ \t]*(?:#[^\r\n]*)?(?:\r?\n)?$"
)
_MAPPING_NODE: Final = TypeAdapter(
    MappingNode, config=ConfigDict(arbitrary_types_allowed=True)
)
_SCALAR_NODE: Final = TypeAdapter(
    ScalarNode, config=ConfigDict(arbitrary_types_allowed=True)
)
_MERGE_TAG: Final = "tag:yaml.org,2002:merge"
_NULL_TAG: Final = "tag:yaml.org,2002:null"


class OverlayReason(StrEnum):
    """Structural error codes never contain user configuration values."""

    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    UNSUPPORTED_MAPPING = "unsupported_mcp_mapping"
    UNSUPPORTED_INDENTATION = "unsupported_indentation"
    AMBIGUOUS_MANAGED_BLOCK = "ambiguous_managed_block"
    UNMANAGED_SERVER = "unmanaged_server_entry"


class ConfigOverlayError(Exception):
    """Refuse unsupported mappings rather than clobber unrelated configuration."""

    reason: OverlayReason

    def __init__(self, reason: OverlayReason) -> None:
        """Record a non-sensitive structural error code."""
        super().__init__()
        self.reason = reason

    @override
    def __str__(self) -> str:
        """Do not disclose configuration content in errors."""
        return f"MCP overlay refused: {self.reason.value}"


class SamplingPolicy(BaseModel):
    """Do not grant this hardware adapter server-initiated model calls."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
    enabled: Literal[False] = False


class ToolSelection(BaseModel):
    """Explicit native Hermes tool allowlist for this adapter."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
    include: tuple[str, ...] = (
        "robot_get_state",
        "robot_get_supply_voltage",
        "robot_get_capabilities",
        "robot_request_motion",
    )


class McpServerEntry(BaseModel):
    """Non-secret stdio server entry; no environment or authentication fields."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
    command: str
    args: tuple[str, ...]
    timeout: Annotated[float, Field(gt=0, le=30)] = 8
    connect_timeout: Annotated[float, Field(gt=0, le=60)] = 20
    sampling: SamplingPolicy = SamplingPolicy()
    tools: ToolSelection = ToolSelection()
    enabled: bool = True


class _MappingData(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, from_attributes=True, arbitrary_types_allowed=True
    )
    value: tuple[tuple[Node, Node], ...]


class _ScalarData(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, from_attributes=True, strict=True
    )
    value: str


def _target_nodes(mapping: MappingNode, name: str) -> list[Node]:
    targets: list[Node] = []
    for key, value in _MappingData.model_validate(mapping).value:
        scalar = _SCALAR_NODE.validate_python(key)
        if scalar.tag == _MERGE_TAG:
            raise ConfigOverlayError(OverlayReason.UNSUPPORTED_MAPPING)
        if _ScalarData.model_validate(scalar).value == name:
            targets.append(value)
    return targets


def _semantic_target_counts(text: str) -> tuple[int, int]:
    try:
        loader = SafeLoader(text)
        try:
            root = loader.get_single_node()
        finally:
            loader.dispose()
        if root is None:
            return 0, 0
        mapping = _MAPPING_NODE.validate_python(root)
        servers = _target_nodes(mapping, "mcp_servers")
        if len(servers) > 1:
            raise ConfigOverlayError(OverlayReason.AMBIGUOUS_MAPPING)
        if not servers:
            return 0, 0
        if servers[0].tag == _NULL_TAG:
            return 1, 0
        server_map = _MAPPING_NODE.validate_python(servers[0])
        owned = _target_nodes(server_map, "furbomek")
        if len(owned) > 1:
            raise ConfigOverlayError(OverlayReason.AMBIGUOUS_MAPPING)
        return 1, len(owned)
    except (YAMLError, ValidationError):
        raise ConfigOverlayError(OverlayReason.AMBIGUOUS_MAPPING) from None


def _owned_span(
    body: list[str], server_key: re.Pattern[str], semantic_servers: int
) -> tuple[int, int]:
    if sum(bool(server_key.match(line)) for line in body) != semantic_servers:
        raise ConfigOverlayError(OverlayReason.AMBIGUOUS_MAPPING)
    starts = [index for index, line in enumerate(body) if line.strip() == _BEGIN]
    stops = [index for index, line in enumerate(body) if line.strip() == _END]
    if len(starts) != len(stops) or len(starts) > 1:
        raise ConfigOverlayError(OverlayReason.AMBIGUOUS_MANAGED_BLOCK)
    start, stop = 0, 0
    if starts:
        start, stop = starts[0], stops[0] + 1
        owned = [line for line in body[start + 1 : stop - 1] if line.strip()]
        if stop <= start or len(owned) != 1 or not server_key.match(owned[0]):
            raise ConfigOverlayError(OverlayReason.AMBIGUOUS_MANAGED_BLOCK)
    outside = body[:start] + body[stop:]
    if any(server_key.match(line) for line in outside):
        raise ConfigOverlayError(OverlayReason.UNMANAGED_SERVER)
    return start, stop


def overlay_mcp_server(text: str, entry: McpServerEntry) -> str:
    """Modify only our marked block, preserving all other user text verbatim.

    Supports the block-mapping form used by Hermes. Inline/flow MCP maps and
    existing unowned furbomek entries are deliberately refused, not rewritten.
    """
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in text else "\n"
    semantic_roots, semantic_servers = _semantic_target_counts(text)
    roots = [
        index
        for index, line in enumerate(lines)
        if _ROOT_KEY.match(line.removeprefix("\ufeff") if index == 0 else line)
    ]
    if (
        semantic_roots != len(roots)
        or len(roots) > 1
        or text.lstrip("\ufeff \t\r\n").startswith(("{", "["))
    ):
        raise ConfigOverlayError(OverlayReason.AMBIGUOUS_MAPPING)
    if not roots:
        prefix = text + (newline if text and not text.endswith("\n") else "")
        return overlay_mcp_server(prefix + "mcp_servers:" + newline, entry)

    root = roots[0]
    header = lines[root].removeprefix("\ufeff") if root == 0 else lines[root]
    if not _BLOCK_HEADER.fullmatch(header):
        raise ConfigOverlayError(OverlayReason.UNSUPPORTED_MAPPING)
    end = next(
        (
            index
            for index in range(root + 1, len(lines))
            if lines[index].strip() and not lines[index].startswith((" ", "\t", "#"))
        ),
        len(lines),
    )
    body = lines[root + 1 : end]
    content = [
        line for line in body if line.strip() and not line.lstrip().startswith("#")
    ]
    indentation = min(
        (len(line) - len(line.lstrip(" ")) for line in content), default=2
    )
    if indentation < 1 or any(line.startswith("\t") for line in content):
        raise ConfigOverlayError(OverlayReason.UNSUPPORTED_INDENTATION)
    indent = " " * indentation
    server_key = re.compile(rf"^{indent}(?:furbomek|'furbomek'|\"furbomek\"):")
    body_start, body_stop = _owned_span(body, server_key, semantic_servers)
    start, stop = root + 1 + body_start, root + 1 + body_stop
    if not lines[root].endswith("\n"):
        lines[root] += newline
    block = [
        indent + _BEGIN + newline,
        indent + "furbomek: " + entry.model_dump_json() + newline,
        indent + _END + newline,
    ]
    return "".join(lines[:start] + block + lines[stop:])
