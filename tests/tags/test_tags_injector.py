"""Tests for source tag injection."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import pytest

from py_doc_tools.config.model import (
    DiagnosticsConfig,
    DocToolsConfig,
    TagsConfig,
)
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.issues.model import DiagnosticIssue
from py_doc_tools.tags.injector import inject_issues, inject_source_tags

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path



def _make_config(**kwargs: object) -> DocToolsConfig:
    config_cls = cast("Callable[..., DocToolsConfig]", DocToolsConfig)
    return config_cls(**kwargs)


def _base_config(tmp_path: Path, tags: TagsConfig | None) -> DocToolsConfig:
    return _make_config(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_tags=tags is not None,
        tags=tags,
    )

def _diagnostics_config(
    tmp_path: Path,
    *,
    inject_source_tags: bool,
) -> DiagnosticsConfig:
    return DiagnosticsConfig(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=False,
        mkdocs_strict=False,
        fail_on_ruff=False,
        fail_on_mkdocs=False,
        inject_source_tags=inject_source_tags,
        clean_before_inject=True,
        clean_legacy_tags=True,
        ruff_targets=["src"],
        ruff_exclude_dirs=[],
        ruff_exclude_files=[],
    )


def test_inject_source_tags_warns_when_disabled_by_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Standalone tag injection warns when disabled by configuration."""
    called = False

    def fake_generate_diagnostics_docs(
        cfg: DocToolsConfig,
        console: Console,
    ) -> int:
        nonlocal called

        _ = cfg
        _ = console

        called = True
        return 0

    monkeypatch.setattr(
        "py_doc_tools.diagnostics.generator.generate_diagnostics_docs",
        fake_generate_diagnostics_docs,
    )

    tags = TagsConfig(
        scan_roots=[tmp_path / "src"],
        exclude_dirs=[],
        exclude_files=[],
        generated_prefix="py-doc-tools",
        dry_run=False,
        clean_legacy=True,
    )

    cfg = _base_config(tmp_path, tags)
    cfg = replace(
        cfg,
        enable_diagnostics=True,
        diagnostics=_diagnostics_config(
            tmp_path,
            inject_source_tags=False,
        ),
    )

    with caplog.at_level(logging.WARNING):
        code = inject_source_tags(cfg, Console())

    assert code == 0
    assert not called
    assert "Source tag injection was requested" in caplog.text
    assert "inject_source_tags = false" in caplog.text


def test_inject_source_tags_delegates_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Standalone tag injection delegates to diagnostics generation."""
    calls: list[DocToolsConfig] = []

    def fake_generate_diagnostics_docs(
        cfg: DocToolsConfig,
        console: Console,
    ) -> int:
        _ = console

        calls.append(cfg)
        return 0

    monkeypatch.setattr(
        "py_doc_tools.diagnostics.generator.generate_diagnostics_docs",
        fake_generate_diagnostics_docs,
    )

    tags = TagsConfig(
        scan_roots=[tmp_path / "src"],
        exclude_dirs=[],
        exclude_files=[],
        generated_prefix="py-doc-tools",
        dry_run=False,
        clean_legacy=True,
    )

    cfg = _base_config(tmp_path, tags)
    cfg = replace(
        cfg,
        enable_diagnostics=True,
        diagnostics=_diagnostics_config(
            tmp_path,
            inject_source_tags=True,
        ),
    )

    code = inject_source_tags(cfg, Console())

    assert code == 0
    assert calls == [cfg]


def test_inject_issues_dry_run_does_not_modify_file(tmp_path: Path) -> None:
    """Dry-run mode reports generated issue tags without modifying source."""
    src = tmp_path / "src"
    src.mkdir()

    file_path = src / "module.py"
    original = "print('hello')\n"
    _ = file_path.write_text(original, encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[src],
            dry_run=True,
            generated_prefix="py-doc-tools",
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    issue = DiagnosticIssue(
        source="Ruff",
        code="T201",
        severity="fixme",
        category="Ruff",
        message="`print` found",
        file_path=file_path,
        line_number=1,
    )

    code = inject_issues(cfg, Console(), [issue])

    assert code == 0
    assert file_path.read_text(encoding="utf-8") == original


def test_inject_issues_writes_generated_tags(tmp_path: Path) -> None:
    """Issue injector writes generated diagnostic tags."""
    src = tmp_path / "src"
    src.mkdir()

    file_path = src / "module.py"
    _ = file_path.write_text(
        "def bad() -> None:\n    print('bad')\n",
        encoding="utf-8",
    )

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[src],
            dry_run=False,
            generated_prefix="py-doc-tools",
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    issue = DiagnosticIssue(
        source="Ruff",
        code="T201",
        severity="fixme",
        category="Ruff",
        message="`print` found",
        file_path=file_path,
        line_number=2,
        column=5,
    )

    code = inject_issues(cfg, Console(), [issue])

    assert code == 0
    content = file_path.read_text(encoding="utf-8")
    assert "    # FIXME[py-doc-tools:Ruff:T201]: `print` found" in content
    assert "    print('bad')" in content


def test_inject_issues_skips_excluded_paths(tmp_path: Path) -> None:
    """Issue injector skips configured dirs and file patterns."""
    src = tmp_path / "src"
    ignored = src / "__pycache__"
    src.mkdir()
    ignored.mkdir()

    keep = src / "keep.py"
    skip = src / "skip.py"
    ignored_file = ignored / "ignored.py"

    _ = keep.write_text("print('keep')\n", encoding="utf-8")
    _ = skip.write_text("print('skip')\n", encoding="utf-8")
    _ = ignored_file.write_text("print('ignored')\n", encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[src],
            dry_run=False,
            generated_prefix="py-doc-tools",
            exclude_dirs=["__pycache__"],
            exclude_files=["skip.py"],
        ),
    )

    issues = [
        DiagnosticIssue(
            source="Ruff",
            code="T201",
            severity="fixme",
            category="Ruff",
            message="keep",
            file_path=keep,
            line_number=1,
        ),
        DiagnosticIssue(
            source="Ruff",
            code="T201",
            severity="fixme",
            category="Ruff",
            message="skip",
            file_path=skip,
            line_number=1,
        ),
        DiagnosticIssue(
            source="Ruff",
            code="T201",
            severity="fixme",
            category="Ruff",
            message="ignored",
            file_path=ignored_file,
            line_number=1,
        ),
    ]

    code = inject_issues(cfg, Console(), issues)

    assert code == 0
    assert "py-doc-tools:Ruff:T201" in keep.read_text(encoding="utf-8")
    assert "py-doc-tools:Ruff:T201" not in skip.read_text(encoding="utf-8")
    assert "py-doc-tools:Ruff:T201" not in ignored_file.read_text(encoding="utf-8")


def test_inject_issues_ignores_non_localized_issues(tmp_path: Path) -> None:
    """Issue injector ignores diagnostics without file or line."""
    src = tmp_path / "src"
    src.mkdir()

    file_path = src / "module.py"
    original = "print('hello')\n"
    _ = file_path.write_text(original, encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[src],
            dry_run=False,
            generated_prefix="py-doc-tools",
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    issue = DiagnosticIssue(
        source="Ruff",
        code="UNKNOWN",
        severity="warning",
        category="Ruff",
        message="Global issue",
    )

    code = inject_issues(cfg, Console(), [issue])

    assert code == 0
    assert file_path.read_text(encoding="utf-8") == original


def test_inject_issues_missing_root(tmp_path: Path) -> None:
    """Issue injector ignores files outside configured scan roots."""
    file_path = tmp_path / "outside.py"
    original = "print('outside')\n"
    _ = file_path.write_text(original, encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[tmp_path / "src"],
            dry_run=False,
            generated_prefix="py-doc-tools",
        ),
    )

    issue = DiagnosticIssue(
        source="Ruff",
        code="T201",
        severity="fixme",
        category="Ruff",
        message="outside",
        file_path=file_path,
        line_number=1,
    )

    code = inject_issues(cfg, Console(), [issue])

    assert code == 0
    assert file_path.read_text(encoding="utf-8") == original


def test_inject_source_tags_missing_config(tmp_path: Path) -> None:
    """Missing tags config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="tags"):
        _ = inject_source_tags(cfg, Console())


def test_inject_issues_missing_config(tmp_path: Path) -> None:
    """Missing tags config raises a dedicated error for issue injection."""
    cfg = _base_config(tmp_path, None)

    issue = DiagnosticIssue(
        source="Ruff",
        code="T201",
        severity="fixme",
        category="Ruff",
        message="`print` found",
        file_path=tmp_path / "module.py",
        line_number=1,
    )

    with pytest.raises(MissingConfigSectionError, match="tags"):
        _ = inject_issues(cfg, Console(), [issue])
