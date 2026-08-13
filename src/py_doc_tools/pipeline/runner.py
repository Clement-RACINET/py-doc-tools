"""Documentation generation pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.api import generate_api_docs, update_api_nav
from py_doc_tools.coverage import run_coverage
from py_doc_tools.mkdocs import run_mkdocs_build

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


def generate_api(cfg: DocToolsConfig, console: Console) -> None:
    """Generate API documentation if enabled."""
    if not cfg.enable_api:
        console.warn("API generation is disabled.")
        return

    nav = generate_api_docs(cfg, console)
    update_api_nav(cfg, nav)
    console.ok("API documentation generated.")


def generate_coverage(cfg: DocToolsConfig, console: Console) -> None:
    """Generate coverage documentation if enabled."""
    if not cfg.enable_coverage:
        console.warn("Coverage generation is disabled.")
        return

    _ = run_coverage(cfg, console)


def generate_all(cfg: DocToolsConfig, console: Console) -> None:
    """Run every enabled documentation generator."""
    if cfg.enable_api:
        generate_api(cfg, console)

    if cfg.enable_coverage:
        generate_coverage(cfg, console)

    _ = run_mkdocs_build(cfg, console, strict=False)
