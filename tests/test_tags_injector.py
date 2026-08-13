"""Tests for source tag injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from py_doc_tools.config.model import DocToolsConfig, TagsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.tags.injector import inject_source_tags

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


def test_inject_source_tags_dry_run_does_not_modify_file(tmp_path: Path) -> None:
    """Dry-run mode reports changes without modifying source."""
    src = tmp_path / "src"
    src.mkdir()
    file_path = src / "module.py"
    original = "# TODO: improve\n"

    _ = file_path.write_text(original, encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[src],
            dry_run=True,
            start_token="# <pydocs>",
            end_token="# </pydocs>",
            markers=["TODO"],
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    code = inject_source_tags(cfg, Console())

    assert code == 0
    assert file_path.read_text(encoding="utf-8") == original


def test_inject_source_tags_writes_tags(tmp_path: Path) -> None:
    """Injector writes tags around matching marker lines."""
    src = tmp_path / "src"
    src.mkdir()
    file_path = src / "module.py"
    _ = file_path.write_text("    # FIXME: fix indentation\n", encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[src],
            dry_run=False,
            start_token="# <pydocs>",
            end_token="# </pydocs>",
            markers=["FIXME"],
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    code = inject_source_tags(cfg, Console())

    assert code == 0
    content = file_path.read_text(encoding="utf-8")
    assert "    # <pydocs>" in content
    assert "    # FIXME: fix indentation" in content
    assert "    # </pydocs>" in content


def test_inject_source_tags_skips_excluded_paths(tmp_path: Path) -> None:
    """Injector skips configured dirs and file patterns."""
    src = tmp_path / "src"
    ignored = src / "__pycache__"
    src.mkdir()
    ignored.mkdir()

    keep = src / "keep.py"
    skip = src / "skip.py"
    ignored_file = ignored / "ignored.py"

    _ = keep.write_text("# TODO: keep\n", encoding="utf-8")
    _ = skip.write_text("# TODO: skip file\n", encoding="utf-8")
    _ = ignored_file.write_text("# TODO: skip dir\n", encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[src],
            dry_run=False,
            markers=["TODO"],
            exclude_dirs=["__pycache__"],
            exclude_files=["skip.py"],
        ),
    )

    code = inject_source_tags(cfg, Console())

    assert code == 0
    assert "# <pydocs>" in keep.read_text(encoding="utf-8")
    assert "# <pydocs>" not in skip.read_text(encoding="utf-8")
    assert "# <pydocs>" not in ignored_file.read_text(encoding="utf-8")


def test_inject_source_tags_no_marker(tmp_path: Path) -> None:
    """Injector leaves files without markers unchanged."""
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
            markers=["TODO"],
        ),
    )

    assert inject_source_tags(cfg, Console()) == 0
    assert file_path.read_text(encoding="utf-8") == original


def test_inject_source_tags_missing_root(tmp_path: Path) -> None:
    """Injector ignores missing scan roots."""
    cfg = _base_config(
        tmp_path,
        TagsConfig(
            scan_roots=[tmp_path / "missing"],
            dry_run=False,
        ),
    )

    assert inject_source_tags(cfg, Console()) == 0


def test_inject_source_tags_missing_config(tmp_path: Path) -> None:
    """Missing tags config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="tags"):
        _ = inject_source_tags(cfg, Console())
