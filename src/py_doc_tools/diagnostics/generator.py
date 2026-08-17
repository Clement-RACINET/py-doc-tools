"""Ruff and MkDocs diagnostics extraction."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console

COMMAND_NOT_FOUND_CODE = 1


def generate_diagnostics_docs(cfg: DocToolsConfig, console: Console) -> int:
    """Generate diagnostics Markdown pages."""
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    cfg.diagnostics.output_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0

    if cfg.diagnostics.enable_ruff:
        exit_code = max(exit_code, _generate_ruff_diagnostics(cfg, console))

    if cfg.diagnostics.enable_mkdocs:
        exit_code = max(exit_code, _generate_mkdocs_diagnostics(cfg, console))

    return exit_code


def _generate_ruff_diagnostics(
    cfg: DocToolsConfig,
    console: Console,
) -> int:
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    command = _build_ruff_command(cfg)

    try:
        result = _run_text_command(command, cwd=cfg.project_root)
    except FileNotFoundError as exc:
        cfg.diagnostics.ruff_output_file.parent.mkdir(parents=True, exist_ok=True)

        _ = cfg.diagnostics.ruff_output_file.write_text(
            _render_command_output(
                "Ruff diagnostics",
                _command_error_output("Ruff command could not be executed.", exc),
                COMMAND_NOT_FOUND_CODE,
                command=command,
            ),
            encoding="utf-8",
        )

        console.ok(f"Ruff diagnostics generated: {cfg.diagnostics.ruff_output_file}")
        return COMMAND_NOT_FOUND_CODE

    output = _combined_output(result.stdout, result.stderr)
    cfg.diagnostics.ruff_output_file.parent.mkdir(parents=True, exist_ok=True)

    _ = cfg.diagnostics.ruff_output_file.write_text(
        _render_command_output(
            "Ruff diagnostics",
            output,
            result.returncode,
            command=command,
        ),
        encoding="utf-8",
    )

    console.ok(f"Ruff diagnostics generated: {cfg.diagnostics.ruff_output_file}")
    return result.returncode


def _generate_mkdocs_diagnostics(
    cfg: DocToolsConfig,
    console: Console,
) -> int:
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    command = [
        sys.executable,
        "-m",
        "mkdocs",
        "build",
        "-f",
        str(cfg.mkdocs_config),
    ]

    if cfg.diagnostics.mkdocs_strict:
        command.append("--strict")

    try:
        result = _run_text_command(command, cwd=cfg.project_root)
    except FileNotFoundError as exc:
        cfg.diagnostics.mkdocs_output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        _ = cfg.diagnostics.mkdocs_output_file.write_text(
            _render_command_output(
                "MkDocs diagnostics",
                _command_error_output("MkDocs command could not be executed.", exc),
                COMMAND_NOT_FOUND_CODE,
                command=command,
            ),
            encoding="utf-8",
        )

        console.ok(
            f"MkDocs diagnostics generated: {cfg.diagnostics.mkdocs_output_file}",
        )
        return COMMAND_NOT_FOUND_CODE

    output = _combined_output(result.stdout, result.stderr)
    cfg.diagnostics.mkdocs_output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _ = cfg.diagnostics.mkdocs_output_file.write_text(
        _render_command_output(
            "MkDocs diagnostics",
            output,
            result.returncode,
            command=command,
        ),
        encoding="utf-8",
    )

    console.ok(
        f"MkDocs diagnostics generated: {cfg.diagnostics.mkdocs_output_file}",
    )
    return result.returncode


def _run_text_command(
    command: Sequence[str],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and capture text output robustly on all platforms.

    Windows may otherwise decode subprocess output with cp1252. Some tools emit
    UTF-8 or arbitrary bytes, which can raise UnicodeDecodeError. Explicit UTF-8
    decoding with replacement prevents diagnostics generation from crashing.
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    return subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _build_ruff_command(cfg: DocToolsConfig) -> list[str]:
    """Build the Ruff diagnostics command from configuration."""
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    targets = _deduplicate_preserving_order(cfg.diagnostics.ruff_targets)

    command = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        *targets,
    ]

    for pattern in _ruff_exclude_patterns(cfg):
        command.extend(["--exclude", pattern])

    return command


def _ruff_exclude_patterns(cfg: DocToolsConfig) -> list[str]:
    """Return configured Ruff exclude patterns."""
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    return _deduplicate_preserving_order(
        [
            *cfg.diagnostics.ruff_exclude_dirs,
            *cfg.diagnostics.ruff_exclude_files,
        ],
    )


def _deduplicate_preserving_order(items: Sequence[str]) -> list[str]:
    """Remove duplicates while preserving input order."""
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result


def _combined_output(stdout: str, stderr: str) -> str:
    if stdout and stderr:
        return f"{stdout}\n{stderr}"

    if stdout:
        return stdout

    if stderr:
        return stderr

    return "No output."


def _command_error_output(message: str, exc: FileNotFoundError) -> str:
    return "\n".join(
        [
            message,
            "",
            str(exc),
        ],
    )


def _render_command_output(
    title: str,
    output: str,
    return_code: int,
    *,
    command: Sequence[str] | None = None,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Return code: `{return_code}`",
        "",
    ]

    if command is not None:
        lines.extend(
            [
                "## Command",
                "",
                "```text",
                _format_command(command),
                "```",
                "",
            ],
        )

    lines.extend(
        [
            "## Output",
            "",
            "```text",
            output.rstrip(),
            "```",
            "",
        ],
    )

    return "\n".join(lines)


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)
