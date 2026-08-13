"""Additional tests for pipeline branches."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import py_doc_tools.pipeline.runner as pipeline_runner
from py_doc_tools.config.model import DocToolsConfig
from py_doc_tools.core.console import Console

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest

SUCCESS_CODE = 0
DIAGNOSTICS_EXIT_CODE = 2
DIAGRAMS_EXIT_CODE = 1


def _make_config(**kwargs: object) -> DocToolsConfig:
    config_cls = cast("Callable[..., DocToolsConfig]", DocToolsConfig)
    return config_cls(**kwargs)


def _base_config(tmp_path: Path) -> DocToolsConfig:
    return _make_config(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_api=False,
        enable_coverage=False,
        enable_examples=True,
        enable_readme=True,
        enable_todo=True,
        enable_diagnostics=True,
        enable_tags=True,
        enable_diagrams=True,
    )


def test_run_all_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pipeline calls all enabled branches."""
    calls: list[str] = []

    def fake_examples(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append("examples")
        return SUCCESS_CODE

    def fake_readme(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append("readme")
        return SUCCESS_CODE

    def fake_todo(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append("todo")
        return SUCCESS_CODE

    def fake_diagnostics(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append("diagnostics")
        return DIAGNOSTICS_EXIT_CODE

    def fake_tags(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append("tags")
        return SUCCESS_CODE

    def fake_diagrams(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append("diagrams")
        return DIAGRAMS_EXIT_CODE

    def fake_build(
        cfg: DocToolsConfig,
        console: Console,
        *,
        strict: bool = False,
    ) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        assert strict is False
        calls.append(f"build:{strict}")
        return SUCCESS_CODE

    monkeypatch.setattr(pipeline_runner, "generate_examples_docs", fake_examples)
    monkeypatch.setattr(pipeline_runner, "generate_readme_docs", fake_readme)
    monkeypatch.setattr(pipeline_runner, "generate_todo_docs", fake_todo)
    monkeypatch.setattr(pipeline_runner, "generate_diagnostics_docs", fake_diagnostics)
    monkeypatch.setattr(pipeline_runner, "inject_source_tags", fake_tags)
    monkeypatch.setattr(pipeline_runner, "generate_class_diagram_docs", fake_diagrams)
    monkeypatch.setattr(pipeline_runner, "run_mkdocs_build", fake_build)

    code = pipeline_runner.run_all(_base_config(tmp_path), Console())

    assert code == DIAGNOSTICS_EXIT_CODE
    assert calls == [
        "examples",
        "readme",
        "todo",
        "diagnostics",
        "tags",
        "diagrams",
        "build:False",
    ]


def test_run_all_accepts_none_return_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pipeline treats None returns from monkeypatched steps as success."""
    cfg = _make_config(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_examples=True,
    )

    def fake_examples(cfg: DocToolsConfig, console: Console) -> None:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

    def fake_build(
        cfg: DocToolsConfig,
        console: Console,
        *,
        strict: bool = False,
    ) -> None:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        assert strict is False

    monkeypatch.setattr(pipeline_runner, "generate_examples_docs", fake_examples)
    monkeypatch.setattr(pipeline_runner, "run_mkdocs_build", fake_build)

    assert pipeline_runner.run_all(cfg, Console()) == SUCCESS_CODE
