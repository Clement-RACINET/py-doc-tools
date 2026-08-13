"""Coverage report generation."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.subprocesses import run_command

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


def run_coverage(cfg: DocToolsConfig, console: Console) -> int:
    """Run pytest and generate an HTML coverage report."""
    if cfg.coverage is None:
        msg = "coverage"
        raise MissingConfigSectionError(msg)

    cov_cfg = cfg.coverage
    package = cov_cfg.package or (cfg.packages[0] if cfg.packages else None)

    if package is None:
        msg = "coverage.package"
        raise MissingConfigSectionError(msg)

    output_dir = _coverage_output_dir(cfg)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"--cov={package}",
        "--cov-report",
        f"html:{output_dir.as_posix()}",
    ]

    if cov_cfg.branch:
        cmd.append("--cov-branch")

    if cov_cfg.quiet:
        cmd.extend(["--no-header", "-q"])

    console.info("Running coverage report.")
    proc = run_command(cmd, cwd=cfg.project_root, check=False)

    if proc.returncode == 0:
        console.ok(f"Coverage report generated: {output_dir}")
    else:
        console.warn("Coverage command returned a non-zero exit code.")

    return proc.returncode


def _coverage_output_dir(cfg: DocToolsConfig) -> Path:
    if cfg.coverage is None:
        msg = "coverage"
        raise MissingConfigSectionError(msg)

    if cfg.coverage.output_dir is not None:
        return cfg.coverage.output_dir

    return cfg.docs_src_dir / "coverage"
