"""Operator-local JSON settings parsing and typed load failures."""

from enum import StrEnum
from pathlib import Path
from typing import override

from pydantic import ValidationError

from furbomek_gateway.guard_models import GuardSettings
from furbomek_gateway.models import GatewaySettings


class SettingsErrorCode(StrEnum):
    """Stable settings load failure categories."""

    FILE_UNREADABLE = "file_unreadable"
    JSON_INVALID = "json_invalid"


class SettingsLoadError(Exception):
    """Non-sensitive settings load failure."""

    code: SettingsErrorCode

    def __init__(self, code: SettingsErrorCode) -> None:
        """Create a typed settings load failure."""
        super().__init__()
        self.code = code

    @override
    def __str__(self) -> str:
        """Return a non-sensitive settings failure code."""
        return f"settings load failed: {self.code.value}"


def load_settings(path: Path) -> GatewaySettings:
    """Load and validate the operator-local JSON settings file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SettingsLoadError(SettingsErrorCode.FILE_UNREADABLE) from error
    try:
        return GatewaySettings.model_validate_json(raw)
    except ValidationError as error:
        raise SettingsLoadError(SettingsErrorCode.JSON_INVALID) from error


def load_guard_settings(path: Path) -> GuardSettings:
    """Load the closed private configuration for the separate Guard server."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SettingsLoadError(SettingsErrorCode.FILE_UNREADABLE) from error
    try:
        return GuardSettings.model_validate_json(raw)
    except ValidationError as error:
        raise SettingsLoadError(SettingsErrorCode.JSON_INVALID) from error
