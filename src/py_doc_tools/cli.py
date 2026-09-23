# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Command-line interface for py-doc-tools."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from py_doc_tools.config import load_config
from py_doc_tools.core.console import Console
from py_doc_tools.diagnostics.generator import generate_diagnostics_docs
from py_doc_tools.diagrams.generator import generate_class_diagram_docs
from py_doc_tools.examples.generator import generate_examples_docs
from py_doc_tools.mkdocs.runner import run_mkdocs_build, run_mkdocs_serve
from py_doc_tools.pipeline.runner import (
    generate_all,
    generate_api,
    generate_coverage,
)
from py_doc_tools.readme.generator import generate_readme_docs
from py_doc_tools.tags.cleaner import clean_generated_source_tags
from py_doc_tools.tags.injector import inject_source_tags
from py_doc_tools.todo.generator import generate_todo_docs

if TYPE_CHECKING:
    from pathlib import Path as PathType

    from py_doc_tools.config.model import DocToolsConfig


UNKNOWN_COMMAND_MESSAGE = "Unknown command"
NO_GENERATION_TARGET_MESSAGE = "No generation target selected"
UNKNOWN_MKDOCS_COMMAND_MESSAGE = "Unknown mkdocs command"
UNKNOWN_CLEAN_COMMAND_MESSAGE = "Unknown clean command"
UNKNOWN_TAGS_COMMAND_MESSAGE = "Unknown tags command"
API_CONFIG_MISSING_MESSAGE = "API configuration is missing"


@dataclass(frozen=True, slots=True)
class CliArgs:
    """Typed CLI arguments."""

    root: str | PathType = "."
    verbose: bool = False
    command: str | None = None

    generate_all: bool = False
    generate_api: bool = False
    generate_coverage: bool = False

    all: bool = False
    api: bool = False
    coverage: bool = False
    examples: bool = False
    readme: bool = False
    todo: bool = False
    diagnostics: bool = False
    tags: bool = False
    diagrams: bool = False

    mkdocs_command: str | None = None
    strict: bool = False

    clean_command: str | None = None
    target: str | None = None

    tags_command: str | None = None
    dry_run: bool = False
    write: bool = False


class GenerateCommand(Protocol):
    """Callable protocol for generate commands."""

    def __call__(self, cfg: DocToolsConfig, console: Console) -> int | None:
        """Run a generate command."""
        raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """Run the py-doc-tools CLI."""
    parser = _build_parser()
    namespace = parser.parse_args(argv)
    args = _namespace_to_args(namespace)

    cfg = load_config(Path(args.root).resolve())
    console = Console(verbose=args.verbose or cfg.verbose)

    result = dispatch(args, cfg, console)
    return 0 if result is None else result


def dispatch(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> int | None:
    """Dispatch parsed CLI arguments."""
    if args.command == "generate":
        return _run_generate(args, cfg, console)

    if args.command == "mkdocs":
        _run_mkdocs(args, cfg, console)

    if args.command == "clean":
        return _run_clean(args, cfg, console)

    if args.command == "tags":
        return _run_tags(args, cfg, console)

    msg = UNKNOWN_COMMAND_MESSAGE
    raise SystemExit(msg)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pydocs")
    _ = parser.add_argument("--root", default=".", help="Project root directory.")
    _ = parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    subparsers = parser.add_subparsers(dest="command")

    generate = subparsers.add_parser(
        "generate",
        help="Generate documentation artifacts.",
    )
    generate_group = generate.add_mutually_exclusive_group(required=True)
    _ = generate_group.add_argument("--all", action="store_true")
    _ = generate_group.add_argument("--api", action="store_true")
    _ = generate_group.add_argument("--coverage", action="store_true")
    _ = generate_group.add_argument("--examples", action="store_true")
    _ = generate_group.add_argument("--readme", action="store_true")
    _ = generate_group.add_argument("--todo", action="store_true")
    _ = generate_group.add_argument("--diagnostics", action="store_true")
    _ = generate_group.add_argument(
        "--tags",
        action="store_true",
        help="Collect diagnostics and inject generated source tags.",
    )
    _ = generate_group.add_argument("--diagrams", action="store_true")

    mkdocs = subparsers.add_parser("mkdocs", help="Run MkDocs commands.")
    mkdocs_subparsers = mkdocs.add_subparsers(
        dest="mkdocs_command",
        required=True,
    )

    mkdocs_build = mkdocs_subparsers.add_parser(
        "build",
        help="Build MkDocs site.",
    )
    _ = mkdocs_build.add_argument("--strict", action="store_true")

    _ = mkdocs_subparsers.add_parser("serve", help="Serve MkDocs site.")

    clean = subparsers.add_parser("clean", help="Clean generated artifacts.")
    _ = clean.add_argument("target", choices=["api"], help="Cleanup target.")

    tags = subparsers.add_parser(
        "tags",
        help="Manage generated diagnostic source tags.",
    )

    tags_subparsers = tags.add_subparsers(
        dest="tags_command",
        required=True,
    )

    tags_inject = tags_subparsers.add_parser(
        "inject",
        help="Collect diagnostics and inject generated source tags.",
    )
    _add_write_mode_options(tags_inject)

    tags_clean = tags_subparsers.add_parser(
        "clean",
        help="Remove generated source tags.",
    )
    _add_write_mode_options(tags_clean)

    return parser


def _add_write_mode_options(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group(required=False)
    _ = mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files.",
    )
    _ = mode.add_argument(
        "--write",
        action="store_true",
        help="Write changes to files.",
    )


def _namespace_to_args(namespace: argparse.Namespace) -> CliArgs:
    raw = cast("dict[str, object]", vars(namespace))

    all_enabled = _bool_arg(raw, "all")
    api_enabled = _bool_arg(raw, "api")
    coverage_enabled = _bool_arg(raw, "coverage")

    return CliArgs(
        root=_str_arg(raw, "root", "."),
        verbose=_bool_arg(raw, "verbose"),
        command=_optional_str_arg(raw, "command"),
        generate_all=all_enabled,
        generate_api=api_enabled,
        generate_coverage=coverage_enabled,
        all=all_enabled,
        api=api_enabled,
        coverage=coverage_enabled,
        examples=_bool_arg(raw, "examples"),
        readme=_bool_arg(raw, "readme"),
        todo=_bool_arg(raw, "todo"),
        diagnostics=_bool_arg(raw, "diagnostics"),
        tags=_bool_arg(raw, "tags"),
        diagrams=_bool_arg(raw, "diagrams"),
        mkdocs_command=_optional_str_arg(raw, "mkdocs_command"),
        strict=_bool_arg(raw, "strict"),
        target=_optional_str_arg(raw, "target"),
        clean_command=_optional_str_arg(raw, "target"),
        tags_command=_optional_str_arg(raw, "tags_command"),
        dry_run=_bool_arg(raw, "dry_run"),
        write=_bool_arg(raw, "write"),
    )


def _run_generate(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> int | None:
    commands: list[tuple[bool, GenerateCommand]] = [
        (args.all or args.generate_all, generate_all),
        (args.api or args.generate_api, generate_api),
        (args.coverage or args.generate_coverage, generate_coverage),
        (args.examples, generate_examples_docs),
        (args.readme, generate_readme_docs),
        (args.todo, generate_todo_docs),
        (args.diagnostics, generate_diagnostics_docs),
        (args.tags, inject_source_tags),
        (args.diagrams, generate_class_diagram_docs),
    ]

    for enabled, command in commands:
        if enabled:
            return command(cfg, console)

    msg = NO_GENERATION_TARGET_MESSAGE
    raise SystemExit(msg)


def _run_mkdocs(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> None:
    if args.mkdocs_command == "build":
        raise SystemExit(run_mkdocs_build(cfg, console, strict=args.strict))

    if args.mkdocs_command == "serve":
        raise SystemExit(run_mkdocs_serve(cfg, console))

    msg = UNKNOWN_MKDOCS_COMMAND_MESSAGE
    raise SystemExit(msg)


def _run_clean(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> int | None:
    target = args.target or args.clean_command

    if target != "api":
        msg = UNKNOWN_CLEAN_COMMAND_MESSAGE
        raise SystemExit(msg)

    if cfg.api is None:
        msg = API_CONFIG_MISSING_MESSAGE
        raise SystemExit(msg)

    if cfg.api.output_dir.exists():
        shutil.rmtree(cfg.api.output_dir)

    console.ok(f"Removed API documentation directory: {cfg.api.output_dir}")
    return None


def _run_tags(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> int | None:
    if args.tags_command == "inject":
        return inject_source_tags(
            _cfg_with_tags_dry_run_override(args, cfg),
            console,
        )

    if args.tags_command == "clean":
        return clean_generated_source_tags(
            cfg,
            console,
            dry_run=_tags_clean_dry_run(args),
        )

    msg = UNKNOWN_TAGS_COMMAND_MESSAGE
    raise SystemExit(msg)


def _cfg_with_tags_dry_run_override(
    args: CliArgs,
    cfg: DocToolsConfig,
) -> DocToolsConfig:
    if cfg.tags is None:
        return cfg

    if args.write:
        tags = replace(cfg.tags, dry_run=False)
        return replace(cfg, tags=tags)

    if args.dry_run:
        tags = replace(cfg.tags, dry_run=True)
        return replace(cfg, tags=tags)

    return cfg


def _tags_clean_dry_run(args: CliArgs) -> bool:
    return not args.write


def _bool_arg(raw: dict[str, object], key: str) -> bool:
    value = raw.get(key, False)
    return value if isinstance(value, bool) else False


def _str_arg(raw: dict[str, object], key: str, default: str) -> str:
    value = raw.get(key, default)
    return value if isinstance(value, str) else default


def _optional_str_arg(raw: dict[str, object], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


if __name__ == "__main__":
    raise SystemExit(main())
