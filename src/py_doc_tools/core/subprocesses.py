"""Subprocess execution helpers."""

from __future__ import annotations

import os
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
    """Run a command in a project directory."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=check,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
