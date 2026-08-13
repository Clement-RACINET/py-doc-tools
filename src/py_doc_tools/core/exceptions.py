"""Core exceptions used by py-doc-tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PyDocToolsError(Exception):
    """Base class for py-doc-tools exceptions."""


class MissingFileError(PyDocToolsError, FileNotFoundError):
    """Raised when an expected file does not exist."""

    def __init__(self, path: Path) -> None:
        """Initialize the exception.

        Args:
            path: Missing file path.
        """
        super().__init__(f"File not found: {path}")


class MarkerError(PyDocToolsError, ValueError):
    """Raised when expected markers cannot be found."""

    def __init__(self, path: Path, start_marker: str, end_marker: str) -> None:
        """Initialize the exception.

        Args:
            path: File containing markers.
            start_marker: Start marker.
            end_marker: End marker.
        """
        message = f"Markers not found in {path}: {start_marker} / {end_marker}"
        super().__init__(message)


class MissingConfigSectionError(PyDocToolsError, ValueError):
    """Raised when an expected configuration section is missing."""

    def __init__(self, section: str) -> None:
        """Initialize the exception.

        Args:
            section: Missing section name.
        """
        super().__init__(f"Configuration section is missing: {section}")
