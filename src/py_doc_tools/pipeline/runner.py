"""Documentation generation pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.api.generator import generate_api_docs
from py_doc_tools.api.nav import update_api_nav
from py_doc_tools.coverage.runner import run_coverage
from py_doc_tools.diagnostics.generator import generate_diagnostics_docs
from py_doc_tools.diagrams.generator import generate_class_diagram_docs
from py_doc_tools.examples.generator import generate_examples_docs
from py_doc_tools.mkdocs.runner import run_mkdocs_build
from py_doc_tools.readme.generator import generate_readme_docs
from py_doc_tools.tags.injector import inject_source_tags
from py_doc_tools.todo.generator import generate_todo_docs

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


def generate_api(cfg: DocToolsConfig, console: Console) -> int:
    """Generate API documentation and update MkDocs navigation."""
    if not cfg.enable_api:
        return 0

    nav_block = generate_api_docs(cfg, console)
    update_api_nav(cfg, nav_block)
    return 0


def generate_coverage(cfg: DocToolsConfig, console: Console) -> int:
    """Generate coverage documentation."""
    if not cfg.enable_coverage:
        return 0

    return run_coverage(cfg, console)


def generate_all(cfg: DocToolsConfig, console: Console) -> int:
    """Run all enabled documentation tasks."""
    return run_all(cfg, console)


def run_all(cfg: DocToolsConfig, console: Console) -> int:
    """Run the full documentation pipeline."""
    exit_code = 0

    if cfg.enable_diagnostics:
        exit_code = max(
            exit_code,
            _as_exit_code(generate_diagnostics_docs(cfg, console)),
        )

    if cfg.enable_tags:
        exit_code = max(exit_code, _as_exit_code(inject_source_tags(cfg, console)))

    if cfg.enable_api:
        exit_code = max(exit_code, _as_exit_code(generate_api(cfg, console)))

    if cfg.enable_examples:
        exit_code = max(
            exit_code,
            _as_exit_code(generate_examples_docs(cfg, console)),
        )

    if cfg.enable_diagrams:
        exit_code = max(
            exit_code,
            _as_exit_code(generate_class_diagram_docs(cfg, console)),
        )

    if cfg.enable_coverage:
        exit_code = max(exit_code, _as_exit_code(generate_coverage(cfg, console)))

    if cfg.enable_todo:
        exit_code = max(exit_code, _as_exit_code(generate_todo_docs(cfg, console)))

    if cfg.enable_readme:
        exit_code = max(
            exit_code,
            _as_exit_code(generate_readme_docs(cfg, console)),
        )

    return max(
        exit_code,
        _as_exit_code(run_mkdocs_build(cfg, console, strict=False)),
    )


def _as_exit_code(value: int | None) -> int:
    return 0 if value is None else value
