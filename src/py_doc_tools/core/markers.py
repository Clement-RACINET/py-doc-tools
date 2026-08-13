"""Marker replacement utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MarkerError, MissingFileError

if TYPE_CHECKING:
    from pathlib import Path


def replace_between_markers(
    *,
    file_path: Path,
    start_marker: str,
    end_marker: str,
    new_block: str,
    preserve_marker_indent: bool = True,
) -> None:
    """Replace file content located between two marker lines.

    Args:
        file_path: Target file.
        start_marker: Start marker text.
        end_marker: End marker text.
        new_block: Replacement block.
        preserve_marker_indent: Whether to prepend marker indentation.
    """
    if not file_path.exists():
        raise MissingFileError(file_path)

    lines = file_path.read_text(encoding="utf-8").splitlines()

    start_i: int | None = None
    end_i: int | None = None
    marker_indent = ""

    for index, line in enumerate(lines):
        if start_marker in line and start_i is None:
            start_i = index
            marker_indent = line[: len(line) - len(line.lstrip())]
            continue

        if end_marker in line and start_i is not None:
            end_i = index
            break

    if start_i is None or end_i is None:
        raise MarkerError(file_path, start_marker, end_marker)

    new_lines = new_block.splitlines()

    if preserve_marker_indent:
        new_lines = [
            f"{marker_indent}{line}" if line.strip() else "" for line in new_lines
        ]

    updated = lines[: start_i + 1] + new_lines + lines[end_i:]
    _ = file_path.write_text(
        "\n".join(updated) + "\n",
        encoding="utf-8",
        newline="\n",
    )
