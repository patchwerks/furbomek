"""Typed semantic preflight for the observer plugin overlay."""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Final, override

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError
from yaml import SafeLoader, YAMLError
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

_MERGE_TAG: Final = "tag:yaml.org,2002:merge"
_NULL_TAG: Final = "tag:yaml.org,2002:null"
_MAP_TAG: Final = "tag:yaml.org,2002:map"

_MAPPING_NODE: Final = TypeAdapter(
    MappingNode, config=ConfigDict(arbitrary_types_allowed=True)
)
_SEQUENCE_NODE: Final = TypeAdapter(
    SequenceNode, config=ConfigDict(arbitrary_types_allowed=True)
)
_SCALAR_NODE: Final = TypeAdapter(
    ScalarNode, config=ConfigDict(arbitrary_types_allowed=True)
)


class ObserverOverlayReason(StrEnum):
    """Non-sensitive reasons for refusing an observer overlay."""

    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    DISABLED = "explicitly_disabled"
    PARTIAL_MANAGED_BLOCK = "partial_managed_block"
    UNSUPPORTED_MAPPING = "unsupported_mapping"
    UNSUPPORTED_INDENTATION = "unsupported_indentation"


class ObserverOverlayError(Exception):
    """Refuse unsafe observer edits without disclosing configuration values."""

    reason: ObserverOverlayReason

    def __init__(self, reason: ObserverOverlayReason) -> None:
        """Record a non-sensitive structural error code."""
        super().__init__()
        self.reason = reason

    @override
    def __str__(self) -> str:
        """Return only a stable structural error code."""
        return f"Observer overlay refused: {self.reason.value}"


@dataclass(frozen=True, slots=True)
class PluginStructure:
    """Semantic target nodes needed by the byte-preserving renderer."""

    plugins: MappingNode | None
    enabled: SequenceNode | None
    enabled_streams: int


class _AliasTrackingLoader(SafeLoader):
    alias_seen: bool

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self.alias_seen = False

    @override
    def fetch_alias(self) -> None:
        self.alias_seen = True
        super().fetch_alias()


class _MappingData(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, from_attributes=True, arbitrary_types_allowed=True
    )
    value: tuple[tuple[Node, Node], ...]


class _SequenceData(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, from_attributes=True, arbitrary_types_allowed=True
    )
    value: tuple[Node, ...]


class _ScalarData(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, from_attributes=True, strict=True
    )
    value: str


def _targets(mapping: MappingNode, name: str) -> list[Node]:
    targets: list[Node] = []
    try:
        for key, value in _MappingData.model_validate(mapping).value:
            scalar = _SCALAR_NODE.validate_python(key)
            if scalar.tag == _MERGE_TAG:
                raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
            if _ScalarData.model_validate(scalar).value == name:
                targets.append(value)
    except ValidationError:
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING) from None
    return targets


def _sequence_node(node: Node) -> SequenceNode:
    try:
        return _SEQUENCE_NODE.validate_python(node)
    except ValidationError:
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING) from None


def _stream_count(sequence: SequenceNode) -> int:
    try:
        values = _SequenceData.model_validate(
            _SEQUENCE_NODE.validate_python(sequence)
        ).value
        return sum(
            _ScalarData.model_validate(_SCALAR_NODE.validate_python(value)).value
            == "furbomek_stream"
            for value in values
        )
    except ValidationError:
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING) from None


def _parse_root(text: str) -> MappingNode | None:
    loader = _AliasTrackingLoader(text)
    root: Node | None = None
    try:
        root = loader.get_single_node()
        alias_seen = loader.alias_seen
    except YAMLError:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING) from None
    finally:
        loader.dispose()
    if alias_seen:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
    if root is None:
        return None
    try:
        mapping = _MAPPING_NODE.validate_python(root)
    except ValidationError:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING) from None
    if mapping.flow_style is True:
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING)
    return mapping


def _plugin_map(node: Node) -> MappingNode:
    try:
        mapping = _MAPPING_NODE.validate_python(node)
    except ValidationError:
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING) from None
    if mapping.flow_style is True:
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING)
    return mapping


def _enabled_node(mapping: MappingNode) -> SequenceNode | None:
    enabled = _targets(mapping, "enabled")
    disabled = _targets(mapping, "disabled")
    if len(enabled) > 1 or len(disabled) > 1:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
    if disabled and _stream_count(_sequence_node(disabled[0])):
        raise ObserverOverlayError(ObserverOverlayReason.DISABLED)
    if not enabled:
        return None
    sequence = _sequence_node(enabled[0])
    if sequence.flow_style is True:
        raise ObserverOverlayError(ObserverOverlayReason.UNSUPPORTED_MAPPING)
    if _stream_count(sequence) > 1:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
    return sequence


def parse_plugin_structure(text: str) -> PluginStructure:
    """Parse target YAML nodes without serializing or rewriting the document."""
    root = _parse_root(text)
    if root is None:
        return PluginStructure(None, None, 0)
    plugins = _targets(root, "plugins")
    if len(plugins) > 1:
        raise ObserverOverlayError(ObserverOverlayReason.AMBIGUOUS_MAPPING)
    if not plugins:
        return PluginStructure(None, None, 0)
    if plugins[0].tag == _NULL_TAG:
        return PluginStructure(MappingNode(_MAP_TAG, []), None, 0)
    plugin_map = _plugin_map(plugins[0])
    enabled = _enabled_node(plugin_map)
    return PluginStructure(
        plugin_map, enabled, 0 if enabled is None else _stream_count(enabled)
    )
