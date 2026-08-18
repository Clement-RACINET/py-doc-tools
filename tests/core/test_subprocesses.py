"""Tests for subprocess helpers."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from py_doc_tools.core.subprocesses import run_command

if TYPE_CHECKING:
    from pathlib import Path


def test_run_command_success(tmp_path: Path) -> None:
    """A simple Python subprocess can be executed."""
    proc = run_command(
        [sys.executable, "-c", "print('hello')"],
        cwd=tmp_path,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert proc.stdout.strip() == "hello"
