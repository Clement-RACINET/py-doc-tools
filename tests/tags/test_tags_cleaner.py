"""Tests for generated source tag cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from py_doc_tools.config.model import DocToolsConfig, TagsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.tags.cleaner import (
    clean_generated_source_tags,
    clean_generated_source_tags_result,
    clean_generated_tags_in_file,
)
from py_doc_tools.tags.generated import is_generated_tag_line

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

ONE_REMOVED_TAG = 1
TWO_REMOVED_TAGS = 2
ONE_SCANNED_FILE = 1
ONE_CHANGED_FILE = 1


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


def test_is_generated_tag_line_detects_current_format() -> None:
    """Generated py-doc-tools tags are detected."""
    line = "# FIXME[py-doc-tools:Ruff:T201]: `print` found"

    assert is_generated_tag_line(line)


def test_is_generated_tag_line_detects_legacy_format() -> None:
    """Legacy generated tags are detected when enabled."""
    line = "# FIXME[Ruff:UP045]: Use `X | None`"

    assert is_generated_tag_line(line, clean_legacy=True)


def test_is_generated_tag_line_can_ignore_legacy_format() -> None:
    """Legacy generated tags can be preserved."""
    line = "# FIXME[Ruff:UP045]: Use `X | None`"

    assert not is_generated_tag_line(line, clean_legacy=False)


def test_is_generated_tag_line_preserves_human_todos() -> None:
    """Human TODO/FIXME comments are not treated as generated tags."""
    assert not is_generated_tag_line("# TODO: improve sampling")
    assert not is_generated_tag_line("# FIXME: business case to investigate")


def test_clean_generated_tags_in_file_writes_changes(tmp_path: Path) -> None:
    """Cleaner removes generated tags from a single file."""
    file_path = tmp_path / "module.py"
    _ = file_path.write_text(
        "\n".join(
            [
                "# TODO: keep human note",
                "# FIXME[py-doc-tools:Ruff:T201]: generated",
                "# FIXME[Ruff:UP045]: legacy generated",
                "print('hello')",
                "",
            ],
        ),
        encoding="utf-8",
    )

    removed = clean_generated_tags_in_file(
        file_path,
        clean_legacy=True,
        dry_run=False,
    )

    content = file_path.read_text(encoding="utf-8")

    assert removed == TWO_REMOVED_TAGS
    assert "# TODO: keep human note" in content
    assert "py-doc-tools:Ruff:T201" not in content
    assert "Ruff:UP045" not in content
    assert "print('hello')" in content


def test_clean_generated_tags_in_file_dry_run_preserves_file(tmp_path: Path) -> None:
    """Dry-run reports removals without modifying the file."""
    file_path = tmp_path / "module.py"
    original = "# FIXME[py-doc-tools:Ruff:T201]: generated\nprint('hello')\n"
    _ = file_path.write_text(original, encoding="utf-8")

    removed = clean_generated_tags_in_file(
        file_path,
        clean_legacy=True,
        dry_run=True,
    )

    assert removed == ONE_REMOVED_TAG
    assert file_path.read_text(encoding="utf-8") == original


def test_clean_generated_source_tags_result_dry_run(tmp_path: Path) -> None:
    """Project-level dry-run returns a summary without writing files."""
    src = tmp_path / "src"
    src.mkdir()

    file_path = src / "module.py"
    original = "# FIXME[py-doc-tools:Ruff:T201]: generated\nprint('hello')\n"
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

    result = clean_generated_source_tags_result(cfg)

    assert result.files_scanned == ONE_SCANNED_FILE
    assert result.files_changed == ONE_CHANGED_FILE
    assert result.removed_tags == ONE_REMOVED_TAG
    assert result.changed_files == [file_path]
    assert file_path.read_text(encoding="utf-8") == original


def test_clean_generated_source_tags_result_write(tmp_path: Path) -> None:
    """Project-level cleanup writes files when dry-run is disabled."""
    src = tmp_path / "src"
    src.mkdir()

    file_path = src / "module.py"
    _ = file_path.write_text(
        "# FIXME[py-doc-tools:Ruff:T201]: generated\n"  # pyright: ignore[reportImplicitStringConcatenation]
        "print('hello')\n",
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

    result = clean_generated_source_tags_result(cfg)

    assert result.files_scanned == 1
    assert result.files_changed == 1
    assert result.removed_tags == 1
    assert "py-doc-tools:Ruff:T201" not in file_path.read_text(encoding="utf-8")


def test_clean_generated_source_tags_override_write(tmp_path: Path) -> None:
    """Explicit dry-run override can force writing despite config dry-run."""
    src = tmp_path / "src"
    src.mkdir()

    file_path = src / "module.py"
    _ = file_path.write_text(
        "# FIXME[py-doc-tools:Ruff:T201]: generated\n"  # pyright: ignore[reportImplicitStringConcatenation]
        "print('hello')\n",
        encoding="utf-8",
    )

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

    code = clean_generated_source_tags(cfg, Console(), dry_run=False)

    assert code == 0
    assert "py-doc-tools:Ruff:T201" not in file_path.read_text(encoding="utf-8")


def test_clean_generated_source_tags_skips_excluded_paths(tmp_path: Path) -> None:
    """Cleaner skips configured directories and file patterns."""
    src = tmp_path / "src"
    ignored = src / "__pycache__"
    src.mkdir()
    ignored.mkdir()

    keep = src / "keep.py"
    skip = src / "skip.py"
    ignored_file = ignored / "ignored.py"

    _ = keep.write_text("# FIXME[py-doc-tools:Ruff:T201]: keep\n", encoding="utf-8")
    _ = skip.write_text("# FIXME[py-doc-tools:Ruff:T201]: skip\n", encoding="utf-8")
    _ = ignored_file.write_text(
        "# FIXME[py-doc-tools:Ruff:T201]: ignored\n",
        encoding="utf-8",
    )

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

    result = clean_generated_source_tags_result(cfg)

    assert result.files_scanned == 1
    assert result.files_changed == 1
    assert result.removed_tags == 1
    assert keep.read_text(encoding="utf-8") == ""
    assert "py-doc-tools:Ruff:T201" in skip.read_text(encoding="utf-8")
    assert "py-doc-tools:Ruff:T201" in ignored_file.read_text(encoding="utf-8")


def test_clean_generated_source_tags_missing_config(tmp_path: Path) -> None:
    """Missing tags config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="tags"):
        _ = clean_generated_source_tags(cfg, Console())
