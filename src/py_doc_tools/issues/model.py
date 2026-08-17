"""Common diagnostic issue model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

IssueSeverity = Literal["todo", "fixme", "warning", "error"]


@dataclass(frozen=True, slots=True)
class DiagnosticIssue:
    """Normalized issue emitted by an external documentation/checking tool."""

    source: str
    code: str
    severity: IssueSeverity
    category: str
    message: str
    file_path: Path | None = None
    line_number: int | None = None
    column: int | None = None

    def is_localized(self) -> bool:
        """Return whether the issue points to a source file and line."""
        return self.file_path is not None and self.line_number is not None
