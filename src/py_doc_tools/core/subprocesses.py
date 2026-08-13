"""Subprocess execution helpers."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    check: bool = False,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command in a project directory.

    Args:
        cmd: Command and arguments.
        cwd: Working directory.
        check: Whether subprocess should raise on non-zero exit.
        capture_output: Whether stdout and stderr should be captured.

    Returns:
        Completed process.
    """
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
