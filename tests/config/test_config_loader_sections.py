"""Tests for optional configuration sections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.config import load_config

if TYPE_CHECKING:
    from pathlib import Path

PREVIEW_MAX_WIDTH = 123
EXPECTED_SCAN_ROOTS_COUNT = 2


def test_load_config_sections(tmp_path: Path) -> None:
    """Loader builds optional sections when their tables exist."""
    _ = (tmp_path / "pyproject.toml").write_text(
        """
[tool.py-doc-tools]
docs_src_dir = "docs"
packages = ["demo"]

[tool.py-doc-tools.examples]
source_dir = "examples"
output_dir = "docs/examples"
assets_dir = "docs/examples/assets"
overview_enabled = false
copy_assets = false
show_image_previews = false
preview_max_width_px = 123
skip_dirs = ["ignored"]
skip_files = ["skip.py"]
asset_extensions = [".png"]

[tool.py-doc-tools.readme]
source_file = "README.md"
output_file = "docs/readme.md"
title = "Custom README"
include_toc_note = false

[tool.py-doc-tools.todo]
output_file = "docs/todo.md"
scan_roots = ["src", "tests"]
markers = ["TODO"]
exclude_dirs = ["ignored"]
exclude_files = ["skip.py"]

[tool.py-doc-tools.diagnostics]
output_dir = "docs/diagnostics"
ruff_output_file = "docs/diagnostics/ruff.md"
mkdocs_output_file = "docs/diagnostics/mkdocs.md"
enable_ruff = false
enable_mkdocs = false
mkdocs_strict = true

[tool.py-doc-tools.tags]
scan_roots = ["src"]
dry_run = false
start_token = "# START"
end_token = "# END"
markers = ["TODO"]
exclude_dirs = ["ignored"]
exclude_files = ["skip.py"]

[tool.py-doc-tools.diagrams]
output_file = "docs/classes.md"
scan_roots = ["src"]
title = "Classes"
exclude_dirs = ["ignored"]
exclude_files = ["skip.py"]
include_private = true
""".strip(),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.examples is not None
    assert cfg.examples.preview_max_width_px == PREVIEW_MAX_WIDTH
    assert cfg.examples.asset_extensions == [".png"]

    assert cfg.readme is not None
    assert cfg.readme.title == "Custom README"
    assert not cfg.readme.include_toc_note

    assert cfg.todo is not None
    assert cfg.todo.markers == ["TODO"]
    assert len(cfg.todo.scan_roots) == EXPECTED_SCAN_ROOTS_COUNT

    assert cfg.diagnostics is not None
    assert not cfg.diagnostics.enable_ruff
    assert not cfg.diagnostics.enable_mkdocs
    assert cfg.diagnostics.mkdocs_strict

    assert cfg.tags is not None
    assert not cfg.tags.dry_run
    assert cfg.tags.start_token == "# START"

    assert cfg.diagrams is not None
    assert cfg.diagrams.title == "Classes"
    assert cfg.diagrams.include_private

def test_examples_config_defaults_to_directory_mode(tmp_path: Path) -> None:
    """Examples config defaults to directory mode and standard folder conventions."""
    pyproject = tmp_path / "pyproject.toml"
    _ = pyproject.write_text(
        "\n".join(
            [
                "[tool.py-doc-tools]",
                "enable_examples = true",
                "",
                "[tool.py-doc-tools.examples]",
                'source_dir = "examples"',
                'output_dir = "docs/src/examples"',
                'assets_dir = "docs/src/examples/assets"',
                "",
            ],
        ),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.examples is not None
    assert cfg.examples.mode == "directory"
    assert cfg.examples.folder_doc_filename == "__doc__.md"
    assert cfg.examples.input_dir_suffix == ".inputs"
    assert cfg.examples.output_dir_suffix == ".outputs"

def test_examples_config_loads_file_mode(tmp_path: Path) -> None:
    """Examples config can explicitly enable legacy file mode."""
    pyproject = tmp_path / "pyproject.toml"
    _ = pyproject.write_text(
        "\n".join(
            [
                "[tool.py-doc-tools]",
                "enable_examples = true",
                "",
                "[tool.py-doc-tools.examples]",
                'mode = "file"',
                'source_dir = "examples"',
                'output_dir = "docs/src/examples"',
                'assets_dir = "docs/src/examples/assets"',
                "",
            ],
        ),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.examples is not None
    assert cfg.examples.mode == "file"
