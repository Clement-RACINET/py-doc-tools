"""MkDocs command runners."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from py_doc_tools.core.subprocesses import run_command

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


def run_mkdocs_build(
    cfg: DocToolsConfig,
    console: Console,
    *,
    strict: bool = False,
) -> int:
    """Run ``mkdocs build``.

    Args:
        cfg: Root tool configuration.
        console: Console logger.
        strict: Whether to pass ``--strict``.

    Returns:
        Process exit code.
    """
    cmd = [sys.executable, "-m", "mkdocs", "build"]

    if strict:
        cmd.append("--strict")

    console.info("Running mkdocs build.")
    proc = run_command(cmd, cwd=cfg.project_root, check=False)

    if proc.returncode == 0:
        console.ok("mkdocs build succeeded.")
    else:
        console.error("mkdocs build failed.")

    return proc.returncode


def run_mkdocs_serve(cfg: DocToolsConfig, console: Console) -> int:
    """Run ``mkdocs serve``.

    Args:
        cfg: Root tool configuration.
        console: Console logger.

    Returns:
        Process exit code.
    """
    cmd = [sys.executable, "-m", "mkdocs", "serve"]

    console.info("Running mkdocs serve.")
    proc = run_command(cmd, cwd=cfg.project_root, check=False)
    return proc.returncode
