"""Tests for coverage MkDocs navigation helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from py_doc_tools.config.model import CoverageConfig, DocToolsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.coverage.nav import (
    build_coverage_nav_block,
    build_coverage_tree,
    inject_coverage_backlinks,
    read_coverage_nav_items,
    render_tree,
    update_coverage_nav,
)

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_NAV_ITEM_COUNT = 2


def _cfg(
    tmp_path: Path,
    *,
    nav_enabled: bool = True,
    inject_backlinks_enabled: bool = True,
    coverage: CoverageConfig | object | None = ...,
) -> DocToolsConfig:
    if coverage is ...:
        coverage_config = CoverageConfig(
            package="demo",
            output_dir=tmp_path / "docs" / "coverage",
            page_file=tmp_path / "docs" / "coverage-report.md",
            nav_enabled=nav_enabled,
            nav_start_marker="# --- AUTOGEN_COVERAGE_START ---",
            nav_end_marker="# --- AUTOGEN_COVERAGE_END ---",
            nav_max_depth=8,
            inject_backlinks=inject_backlinks_enabled,
            backlink_label="← Back to documentation",
        )
    else:
        coverage_config = coverage

    return DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_coverage=True,
        coverage=coverage_config,
    )


def _write_html_file(path: Path, *, body: str = "<body>") -> None:
    if body == "<body>":
        content = "<html><body></body></html>"
    elif body == "<body class>":
        content = '<html><body class="coverage"></body></html>'
    else:
        content = "<html></html>"

    _ = path.write_text(content, encoding="utf-8")


def _write_status_json(tmp_path: Path) -> Path:
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    html_files = [
        "index.html",
        "class_index.html",
        "function_index.html",
        "z_core_client_py.html",
        "z_core_env_py.html",
    ]

    for filename in html_files:
        _write_html_file(coverage_dir / filename)

    status = {
        "files": {
            "abb_rws_client_python_rw6/core/client.py": {
                "index": "z_core_client_py.html",
            },
            "abb_rws_client_python_rw6/core/env.py": {
                "index": "z_core_env_py.html",
            },
        },
    }

    status_file = coverage_dir / "status.json"
    _ = status_file.write_text(json.dumps(status), encoding="utf-8")
    return status_file


def test_read_coverage_nav_items_from_status_json(tmp_path: Path) -> None:
    """Coverage nav items are extracted from coverage.py status.json."""
    _ = _write_status_json(tmp_path)

    items = read_coverage_nav_items(tmp_path / "docs" / "coverage")

    assert len(items) == EXPECTED_NAV_ITEM_COUNT
    assert items[0].source_path == "abb_rws_client_python_rw6/core/client.py"
    assert items[0].html_path.name == "z_core_client_py.html"


def test_build_coverage_nav_block(tmp_path: Path) -> None:
    """Coverage nav block contains overview, indexes and file tree."""
    _ = _write_status_json(tmp_path)

    block = build_coverage_nav_block(
        docs_src_dir=tmp_path / "docs",
        output_dir=tmp_path / "docs" / "coverage",
        page_file=tmp_path / "docs" / "coverage-report.md",
        max_depth=8,
    )

    assert "- Overview: coverage-report.md" in block
    assert "- HTML index: coverage/index.html" in block
    assert "- Class index: coverage/class_index.html" in block
    assert "- Function index: coverage/function_index.html" in block
    assert "- Files:" in block
    assert "- abb_rws_client_python_rw6:" in block
    assert "- core:" in block
    assert "- client.py: coverage/z_core_client_py.html" in block
    assert "- env.py: coverage/z_core_env_py.html" in block


def test_update_coverage_nav_replaces_markers(tmp_path: Path) -> None:
    """Coverage nav is injected between configured MkDocs markers."""
    cfg = _cfg(tmp_path)
    _ = _write_status_json(tmp_path)

    mkdocs = """site_name: Demo

nav:
  - Home: index.md
  - Coverage:
      # --- AUTOGEN_COVERAGE_START ---
      - Old: old.md
      # --- AUTOGEN_COVERAGE_END ---
"""

    _ = cfg.mkdocs_config.write_text(mkdocs, encoding="utf-8")

    update_coverage_nav(cfg, Console())

    content = cfg.mkdocs_config.read_text(encoding="utf-8")

    assert "- Old: old.md" not in content
    assert "- Overview: coverage-report.md" in content
    assert "- client.py: coverage/z_core_client_py.html" in content


def test_update_coverage_nav_returns_when_disabled(tmp_path: Path) -> None:
    """Disabled coverage nav does not require mkdocs.yml markers."""
    cfg = _cfg(tmp_path, nav_enabled=False)

    update_coverage_nav(cfg, Console())

    assert not cfg.mkdocs_config.exists()


def test_update_coverage_nav_missing_config_raises(tmp_path: Path) -> None:
    """Missing coverage config raises a dedicated error."""
    cfg = _cfg(tmp_path, coverage=None)

    with pytest.raises(MissingConfigSectionError, match="coverage"):
        update_coverage_nav(cfg, Console())


def test_inject_coverage_backlinks(tmp_path: Path) -> None:
    """Coverage HTML pages receive a backlink to documentation."""
    cfg = _cfg(tmp_path)
    _ = _write_status_json(tmp_path)

    inject_coverage_backlinks(cfg, Console())

    content = (
        tmp_path / "docs" / "coverage" / "z_core_client_py.html"
    ).read_text(encoding="utf-8")

    assert "py-doc-tools-coverage-backlink" in content
    assert "← Back to documentation" in content
    assert 'href="../coverage-report"' in content


def test_inject_coverage_backlinks_returns_when_disabled(tmp_path: Path) -> None:
    """Disabled backlink injection leaves files unchanged."""
    cfg = _cfg(tmp_path, inject_backlinks_enabled=False)
    _ = _write_status_json(tmp_path)

    html_file = tmp_path / "docs" / "coverage" / "z_core_client_py.html"
    before = html_file.read_text(encoding="utf-8")

    inject_coverage_backlinks(cfg, Console())

    assert html_file.read_text(encoding="utf-8") == before


def test_inject_coverage_backlinks_missing_config_raises(tmp_path: Path) -> None:
    """Missing coverage config raises a dedicated error."""
    cfg = _cfg(tmp_path, coverage=None)

    with pytest.raises(MissingConfigSectionError, match="coverage"):
        inject_coverage_backlinks(cfg, Console())


def test_inject_coverage_backlinks_missing_output_dir_returns(tmp_path: Path) -> None:
    """Missing coverage output directory is ignored."""
    cfg = _cfg(tmp_path)

    inject_coverage_backlinks(cfg, Console())

    assert not (tmp_path / "docs" / "coverage").exists()


def test_inject_coverage_backlinks_handles_body_with_attributes(
    tmp_path: Path,
) -> None:
    """Backlink injection supports body tags with attributes."""
    cfg = _cfg(tmp_path)
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    html_file = coverage_dir / "custom.html"
    _write_html_file(html_file, body="<body class>")

    inject_coverage_backlinks(cfg, Console())

    content = html_file.read_text(encoding="utf-8")
    assert "py-doc-tools-coverage-backlink" in content
    assert '<body class="coverage">' in content


def test_inject_coverage_backlinks_ignores_files_without_body(
    tmp_path: Path,
) -> None:
    """Files without body tags are left unchanged."""
    cfg = _cfg(tmp_path)
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    html_file = coverage_dir / "custom.html"
    _write_html_file(html_file, body="none")

    before = html_file.read_text(encoding="utf-8")

    inject_coverage_backlinks(cfg, Console())

    assert html_file.read_text(encoding="utf-8") == before


def test_inject_coverage_backlinks_is_idempotent(tmp_path: Path) -> None:
    """Backlink injection does not duplicate existing backlinks."""
    cfg = _cfg(tmp_path)
    _ = _write_status_json(tmp_path)

    html_file = tmp_path / "docs" / "coverage" / "z_core_client_py.html"

    inject_coverage_backlinks(cfg, Console())
    once = html_file.read_text(encoding="utf-8")

    inject_coverage_backlinks(cfg, Console())
    twice = html_file.read_text(encoding="utf-8")

    assert twice == once
    assert twice.count("py-doc-tools-coverage-backlink") == 1


def test_read_coverage_nav_items_missing_status_returns_empty(tmp_path: Path) -> None:
    """Missing status.json results in an empty item list."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    assert read_coverage_nav_items(coverage_dir) == []


def test_read_coverage_nav_items_invalid_json_returns_empty(tmp_path: Path) -> None:
    """Invalid status.json results in an empty item list."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    _ = (coverage_dir / "status.json").write_text("{", encoding="utf-8")

    assert read_coverage_nav_items(coverage_dir) == []


def test_read_coverage_nav_items_non_object_json_returns_empty(
    tmp_path: Path,
) -> None:
    """Non-object status.json results in an empty item list."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    _ = (coverage_dir / "status.json").write_text("[]", encoding="utf-8")

    assert read_coverage_nav_items(coverage_dir) == []


def test_read_coverage_nav_items_missing_files_returns_empty(tmp_path: Path) -> None:
    """Status without files table results in an empty item list."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    _ = (coverage_dir / "status.json").write_text("{}", encoding="utf-8")

    assert read_coverage_nav_items(coverage_dir) == []


def test_read_coverage_nav_items_ignores_invalid_file_entries(
    tmp_path: Path,
) -> None:
    """Invalid file entries are skipped."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    status = {
        "files": {
            "valid.py": {
                "index": "valid_py.html",
            },
            "missing_html.py": {
                "index": "missing_py.html",
            },
            12: {
                "index": "invalid_key.html",
            },
            "invalid_value.py": "not-a-table",
            "missing_index.py": {
                "filename": "missing_index.py",
            },
        },
    }

    _write_html_file(coverage_dir / "valid_py.html")
    _ = (coverage_dir / "status.json").write_text(
        json.dumps(status),
        encoding="utf-8",
    )

    items = read_coverage_nav_items(coverage_dir)

    assert len(items) == 1
    assert items[0].source_path == "valid.py"
    assert items[0].html_path.name == "valid_py.html"


def test_read_coverage_nav_items_supports_alternative_fields(
    tmp_path: Path,
) -> None:
    """Alternative coverage status fields are supported."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    _write_html_file(coverage_dir / "alt_py.html")

    status = {
        "files": {
            "internal-key": {
                "relative_filename": "pkg/alt.py",
                "html_filename": "alt_py.html",
            },
        },
    }

    _ = (coverage_dir / "status.json").write_text(
        json.dumps(status),
        encoding="utf-8",
    )

    items = read_coverage_nav_items(coverage_dir)

    assert len(items) == 1
    assert items[0].source_path == "pkg/alt.py"
    assert items[0].html_path.name == "alt_py.html"


def test_build_coverage_nav_block_without_optional_indexes(
    tmp_path: Path,
) -> None:
    """Coverage nav block can be built without optional index pages."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    _ = (coverage_dir / "status.json").write_text(
        json.dumps({"files": {}}),
        encoding="utf-8",
    )

    block = build_coverage_nav_block(
        docs_src_dir=tmp_path / "docs",
        output_dir=coverage_dir,
        page_file=tmp_path / "docs" / "coverage-report.md",
        max_depth=8,
    )

    assert block == "- Overview: coverage-report.md"


def test_build_coverage_tree_truncates_deep_paths(tmp_path: Path) -> None:
    """Deep source paths are truncated according to max_depth."""
    coverage_dir = tmp_path / "docs" / "coverage"
    coverage_dir.mkdir(parents=True)

    html_file = coverage_dir / "deep_py.html"
    _write_html_file(html_file)

    from py_doc_tools.coverage.nav import CoverageNavItem  # noqa: PLC0415

    tree = build_coverage_tree(
        [
            CoverageNavItem(
                source_path="a/b/c/d/e/deep.py",
                html_path=html_file,
            ),
        ],
        docs_src_dir=tmp_path / "docs",
        max_depth=3,
    )

    rendered = "\n".join(render_tree(tree))

    assert "- ...:" in rendered
    assert "- c:" not in rendered
    assert "- d:" in rendered
    assert "- e:" in rendered
    assert "- deep.py: coverage/deep_py.html" in rendered


def test_render_tree_renders_leaf_and_nested_nodes(tmp_path: Path) -> None:  # noqa: ARG001
    """Tree rendering handles nested nodes and leaves."""
    tree = {
        "pkg": {
            "core": {
                "client.py": "coverage/client.html",
            },
        },
        "single.py": "coverage/single.html",
    }

    lines = render_tree(tree)

    assert "- pkg:" in lines
    assert "    - core:" in lines
    assert "        - client.py: coverage/client.html" in lines
    assert "- single.py: coverage/single.html" in lines
