"""Command-line interface for py-doc-tools."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from py_doc_tools.config import DocToolsConfig, load_config
from py_doc_tools.core.console import Console
from py_doc_tools.core.filesystem import remove_dir
from py_doc_tools.mkdocs import run_mkdocs_build, run_mkdocs_serve
from py_doc_tools.pipeline import generate_all, generate_api, generate_coverage


@dataclass(frozen=True, slots=True)
class CliArgs:
    """Typed CLI arguments."""

    root: Path
    verbose: bool
    command: str
    generate_all: bool
    generate_api: bool
    generate_coverage: bool
    mkdocs_command: str | None
    strict: bool
    clean_command: str | None


def main(argv: list[str] | None = None) -> None:
    """Run the py-doc-tools CLI.

    Args:
        argv: Optional argument list.
    """
    parser = build_parser()
    namespace = parser.parse_args(argv)
    args = _parse_namespace(namespace)

    cfg = load_config(args.root)

    console = Console(verbose=args.verbose or cfg.verbose)
    console.configure()

    try:
        dispatch(args, cfg, console)
    except Exception as exc:
        console.error(str(exc))
        raise SystemExit(1) from exc


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="pydocs",
        description="Configurable MkDocs documentation tooling.",
    )
    _ = parser.add_argument(
        "--root",
        default=".",
        help="Project root directory.",
    )
    _ = parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate documentation assets.")
    generate_group = generate.add_mutually_exclusive_group(required=True)
    _ = generate_group.add_argument(
        "--all",
        action="store_true",
        dest="generate_all",
        help="Run all enabled generators.",
    )
    _ = generate_group.add_argument(
        "--api",
        action="store_true",
        dest="generate_api",
        help="Generate API docs.",
    )
    _ = generate_group.add_argument(
        "--coverage",
        action="store_true",
        dest="generate_coverage",
        help="Generate coverage report.",
    )

    mkdocs = subparsers.add_parser("mkdocs", help="Run MkDocs commands.")
    mkdocs_sub = mkdocs.add_subparsers(dest="mkdocs_command", required=True)

    build = mkdocs_sub.add_parser("build", help="Run mkdocs build.")
    _ = build.add_argument(
        "--strict",
        action="store_true",
        help="Run mkdocs build --strict.",
    )

    _ = mkdocs_sub.add_parser("serve", help="Run mkdocs serve.")

    clean = subparsers.add_parser("clean", help="Clean generated assets.")
    clean_sub = clean.add_subparsers(dest="clean_command", required=True)
    _ = clean_sub.add_parser("api", help="Clean generated API directory.")

    return parser


def dispatch(args: CliArgs, cfg: DocToolsConfig, console: Console) -> None:
    """Dispatch a parsed command."""
    if args.command == "generate":
        _dispatch_generate(args, cfg, console)
        return

    if args.command == "mkdocs":
        _dispatch_mkdocs(args, cfg, console)
        return

    if args.command == "clean":
        _dispatch_clean(args, cfg, console)
        return

    _die(f"Unknown command: {args.command}")


def _dispatch_generate(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> None:
    if args.generate_all:
        generate_all(cfg, console)
        return

    if args.generate_api:
        generate_api(cfg, console)
        return

    if args.generate_coverage:
        generate_coverage(cfg, console)
        return

    _die("No generation target selected.")


def _dispatch_mkdocs(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> None:
    if args.mkdocs_command == "build":
        code = run_mkdocs_build(cfg, console, strict=args.strict)
        raise SystemExit(code)

    if args.mkdocs_command == "serve":
        code = run_mkdocs_serve(cfg, console)
        raise SystemExit(code)

    _die(f"Unknown mkdocs command: {args.mkdocs_command}")


def _dispatch_clean(
    args: CliArgs,
    cfg: DocToolsConfig,
    console: Console,
) -> None:
    if args.clean_command == "api":
        if cfg.api is None:
            _die("API configuration is missing.")

        remove_dir(cfg.api.output_dir)
        console.ok(f"Removed API directory: {cfg.api.output_dir}")
        return

    _die(f"Unknown clean command: {args.clean_command}")


def _parse_namespace(namespace: argparse.Namespace) -> CliArgs:
    root_raw = _get_str_attr(namespace, "root", ".")
    command = _get_str_attr(namespace, "command", "")
    mkdocs_command = _get_optional_str_attr(namespace, "mkdocs_command")
    clean_command = _get_optional_str_attr(namespace, "clean_command")

    return CliArgs(
        root=Path(root_raw).resolve(),
        verbose=_get_bool_attr(namespace, "verbose"),
        command=command,
        generate_all=_get_bool_attr(namespace, "generate_all"),
        generate_api=_get_bool_attr(namespace, "generate_api"),
        generate_coverage=_get_bool_attr(namespace, "generate_coverage"),
        mkdocs_command=mkdocs_command,
        strict=_get_bool_attr(namespace, "strict"),
        clean_command=clean_command,
    )


def _get_str_attr(
    namespace: argparse.Namespace,
    name: str,
    default: str,
) -> str:
    value = getattr(namespace, name, default)

    if isinstance(value, str):
        return value

    return default


def _get_optional_str_attr(
    namespace: argparse.Namespace,
    name: str,
) -> str | None:
    value = getattr(namespace, name, None)

    if value is None:
        return None

    if isinstance(value, str):
        return value

    return None


def _get_bool_attr(namespace: argparse.Namespace, name: str) -> bool:
    value = getattr(namespace, name, False)
    return value if isinstance(value, bool) else False


def _die(message: str) -> NoReturn:
    raise SystemExit(message)
