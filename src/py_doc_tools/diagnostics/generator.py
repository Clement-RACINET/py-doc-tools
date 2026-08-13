"""Ruff and MkDocs diagnostics extraction."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
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

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            cwd=cfg.project_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        cfg.diagnostics.ruff_output_file.parent.mkdir(parents=True, exist_ok=True)

        _ = cfg.diagnostics.ruff_output_file.write_text(
            _render_command_output(
                "Ruff diagnostics",
                _command_error_output("Ruff command could not be executed.", exc),
                COMMAND_NOT_FOUND_CODE,
            ),
            encoding="utf-8",
        )

        console.ok(f"Ruff diagnostics generated: {cfg.diagnostics.ruff_output_file}")
        return COMMAND_NOT_FOUND_CODE

    output = _combined_output(result.stdout, result.stderr)
    cfg.diagnostics.ruff_output_file.parent.mkdir(parents=True, exist_ok=True)

    _ = cfg.diagnostics.ruff_output_file.write_text(
        _render_command_output("Ruff diagnostics", output, result.returncode),
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
        result = subprocess.run(
            command,
            cwd=cfg.project_root,
            check=False,
            capture_output=True,
            text=True,
        )
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
        _render_command_output("MkDocs diagnostics", output, result.returncode),
        encoding="utf-8",
    )

    console.ok(
        f"MkDocs diagnostics generated: {cfg.diagnostics.mkdocs_output_file}",
    )
    return result.returncode


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


def _render_command_output(title: str, output: str, return_code: int) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"Return code: `{return_code}`",
            "",
            "```text",
            output.rstrip(),
            "```",
            "",
        ],
    )
