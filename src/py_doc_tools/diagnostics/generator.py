"""Diagnostics extraction, reporting and source tag injection."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.diagnostics.ruff import build_ruff_json_command, collect_ruff_issues
from py_doc_tools.issues.model import DiagnosticIssue
from py_doc_tools.tags.cleaner import clean_generated_source_tags
from py_doc_tools.tags.injector import inject_issues

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console
    from py_doc_tools.issues.model import DiagnosticIssue

COMMAND_NOT_FOUND_CODE = 1


@dataclass(frozen=True, slots=True)
class IssuesOutputContext:
    """Context used to render parsed diagnostics output."""

    title: str
    issues: list[DiagnosticIssue]
    raw_output: str
    return_code: int
    command: Sequence[str]
    project_root: Path


def generate_diagnostics_docs(cfg: DocToolsConfig, console: Console) -> int:
    """Generate diagnostics reports and optionally inject source tags.

    Diagnostics are non-blocking by default. Ruff/MkDocs failures are captured
    as documentation artifacts unless fail_on_* options are enabled.
    """
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    cfg.diagnostics.output_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    collected_issues: list[DiagnosticIssue] = []

    can_inject_source_tags = cfg.diagnostics.inject_source_tags and cfg.tags is not None

    if cfg.diagnostics.inject_source_tags and cfg.tags is None:
        console.warn(
            "Source tag injection requested but tags configuration is missing.",
        )

    if cfg.diagnostics.clean_before_inject and can_inject_source_tags:
        _ = clean_generated_source_tags(cfg, console)

    if cfg.diagnostics.enable_ruff:
        ruff_issues, ruff_code = _generate_ruff_diagnostics(cfg, console)
        collected_issues.extend(ruff_issues)

        if cfg.diagnostics.fail_on_ruff:
            exit_code = max(exit_code, ruff_code)

    if can_inject_source_tags and collected_issues:
        _ = inject_issues(cfg, console, collected_issues)

    if cfg.diagnostics.enable_mkdocs:
        mkdocs_code = _generate_mkdocs_diagnostics(cfg, console)

        if cfg.diagnostics.fail_on_mkdocs:
            exit_code = max(exit_code, mkdocs_code)

    return exit_code


def _generate_ruff_diagnostics(
    cfg: DocToolsConfig,
    console: Console,
) -> tuple[list[DiagnosticIssue], int]:
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    command = build_ruff_json_command(cfg)

    try:
        issues, return_code, raw_output = collect_ruff_issues(cfg)
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
        return [], COMMAND_NOT_FOUND_CODE

    cfg.diagnostics.ruff_output_file.parent.mkdir(parents=True, exist_ok=True)

    _ = cfg.diagnostics.ruff_output_file.write_text(
        _render_issues_output(
            IssuesOutputContext(
                title="Ruff diagnostics",
                issues=issues,
                raw_output=raw_output,
                return_code=return_code,
                command=command,
                project_root=cfg.project_root,
            ),
        ),
        encoding="utf-8",
    )

    message = (
        f"Ruff diagnostics generated: {cfg.diagnostics.ruff_output_file} "
        f"({len(issues)} issue(s))."
    )
    console.ok(message)

    return issues, return_code


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
    """Run a subprocess and capture text output robustly on all platforms."""
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


def _render_issues_output(context: IssuesOutputContext) -> str:
    lines = [
        f"# {context.title}",
        "",
        f"Return code: `{context.return_code}`",
        "",
        f"Issues: `{len(context.issues)}`",
        "",
        "## Command",
        "",
        "```text",
        _format_command(context.command),
        "```",
        "",
    ]

    if context.issues:
        lines.extend(
            [
                "## Parsed issues",
                "",
                "| Code | File | Line | Message |",
                "|---|---|---:|---|",
            ],
        )

        for issue in context.issues:
            file_label = ""
            if issue.file_path is not None:
                try:
                    file_label = issue.file_path.relative_to(
                        context.project_root,
                    ).as_posix()
                except ValueError:
                    file_label = issue.file_path.as_posix()

            message = issue.message.replace("|", "\\|")
            line = issue.line_number or 0
            lines.append(
                f"| `{issue.code}` | `{file_label}` | {line} | {message} |",
            )

        lines.append("")

    lines.extend(
        [
            "## Raw output",
            "",
            "```text",
            context.raw_output.rstrip() or "No output.",
            "```",
            "",
        ],
    )

    return "\n".join(lines)


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
