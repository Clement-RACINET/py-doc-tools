"""Tests for pipeline orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import py_doc_tools.pipeline.runner as pipeline_runner
from py_doc_tools.config.model import CoverageConfig, DocToolsConfig
from py_doc_tools.core.console import Console

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

SUCCESS_CODE = 0


def _base_config(tmp_path: Path) -> DocToolsConfig:
    return DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_api=True,
        enable_coverage=True,
        coverage=CoverageConfig(package="demo"),
    )


def test_generate_api_disabled(tmp_path: Path) -> None:
    """Disabled API generation is skipped."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_api=False,
    )

    pipeline_runner.generate_api(cfg, Console())


def test_generate_coverage_disabled(tmp_path: Path) -> None:
    """Disabled coverage generation is skipped."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_coverage=False,
    )

    pipeline_runner.generate_coverage(cfg, Console())


def test_generate_api_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Enabled API generation calls generator and nav updater."""
    calls: list[str] = []

    def fake_generate_api_docs(cfg: DocToolsConfig, console: Console) -> str:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append("generate")

        return "- Demo: api/demo.md"

    def fake_update_api_nav(cfg: DocToolsConfig, nav_block: str) -> None:
        assert cfg.project_root == tmp_path
        calls.append(nav_block)

    monkeypatch.setattr(
        pipeline_runner,
        "generate_api_docs",
        fake_generate_api_docs,
    )
    monkeypatch.setattr(pipeline_runner, "update_api_nav", fake_update_api_nav)

    pipeline_runner.generate_api(_base_config(tmp_path), Console())

    assert calls == ["generate", "- Demo: api/demo.md"]


def test_generate_coverage_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Enabled coverage generation calls coverage runner."""
    calls: list[str] = []

    def fake_run_coverage(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append("coverage")

        return SUCCESS_CODE

    monkeypatch.setattr(pipeline_runner, "run_coverage", fake_run_coverage)

    pipeline_runner.generate_coverage(_base_config(tmp_path), Console())

    assert calls == ["coverage"]


def test_generate_all(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Full generation pipeline calls enabled stages and build."""
    calls: list[str] = []

    def fake_generate_api(cfg: DocToolsConfig, console: Console) -> None:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append("api")

    def fake_generate_coverage(cfg: DocToolsConfig, console: Console) -> None:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append("coverage")

    def fake_run_mkdocs_build(
        cfg: DocToolsConfig,
        console: Console,
        *,
        strict: bool = False,
    ) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append(f"build:{strict}")

        return SUCCESS_CODE

    monkeypatch.setattr(pipeline_runner, "generate_api", fake_generate_api)
    monkeypatch.setattr(pipeline_runner, "generate_coverage", fake_generate_coverage)
    monkeypatch.setattr(pipeline_runner, "run_mkdocs_build", fake_run_mkdocs_build)

    pipeline_runner.generate_all(_base_config(tmp_path), Console())

    assert calls == ["api", "coverage", "build:False"]
