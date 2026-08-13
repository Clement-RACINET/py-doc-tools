"""Tests for custom exception classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.config.exceptions import (
    ConfigError,
    ConfigTableError,
    ConfigTypeError,
)
from py_doc_tools.core.exceptions import (
    MarkerError,
    MissingConfigSectionError,
    MissingFileError,
    PyDocToolsError,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_config_error_base_class() -> None:
    """ConfigError can be instantiated directly."""
    exc = ConfigError("config failed")

    assert str(exc) == "config failed"


def test_config_type_error_message() -> None:
    """ConfigTypeError formats its message."""
    exc = ConfigTypeError("field", "a string")

    assert str(exc) == "`field` must be a string."


def test_config_table_error_message() -> None:
    """ConfigTableError formats its message."""
    exc = ConfigTableError("api")

    assert str(exc) == "`api` must be a TOML table."


def test_core_error_base_class() -> None:
    """PyDocToolsError can be instantiated directly."""
    exc = PyDocToolsError("tool failed")

    assert str(exc) == "tool failed"


def test_missing_file_error_message(tmp_path: Path) -> None:
    """MissingFileError formats its message."""
    file_path = tmp_path / "missing.txt"
    exc = MissingFileError(file_path)

    assert str(exc) == f"File not found: {file_path}"


def test_marker_error_message(tmp_path: Path) -> None:
    """MarkerError formats its message."""
    file_path = tmp_path / "mkdocs.yml"
    exc = MarkerError(file_path, "START", "END")

    assert str(exc) == f"Markers not found in {file_path}: START / END"


def test_missing_config_section_error_message() -> None:
    """MissingConfigSectionError formats its message."""
    exc = MissingConfigSectionError("api")

    assert str(exc) == "Configuration section is missing: api"
