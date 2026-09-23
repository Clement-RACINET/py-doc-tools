# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for examples documentation generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from py_doc_tools.config.model import DocToolsConfig, ExamplesConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.examples.generator import generate_examples_docs

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

PREVIEW_MAX_WIDTH = 300


def _make_config(**kwargs: object) -> DocToolsConfig:
    config_cls = cast("Callable[..., DocToolsConfig]", DocToolsConfig)
    return config_cls(**kwargs)


def _make_examples_config(**kwargs: object) -> ExamplesConfig:
    config_cls = cast("Callable[..., ExamplesConfig]", ExamplesConfig)
    return config_cls(**kwargs)


def _examples_config(tmp_path: Path, *, mode: str = "directory") -> ExamplesConfig:
    return _make_examples_config(
        source_dir=tmp_path / "examples",
        output_dir=tmp_path / "docs" / "examples",
        assets_dir=tmp_path / "docs" / "examples" / "assets",
        mode=mode,
        nav_start_marker="# --- AUTOGEN_EXAMPLES_START ---",
        nav_end_marker="# --- AUTOGEN_EXAMPLES_END ---",
        overview_enabled=True,
        copy_assets=True,
        show_image_previews=True,
        preview_max_width_px=PREVIEW_MAX_WIDTH,
        clean_output_dir=True,
        skip_dirs=["ignored"],
        skip_files=["skip.py"],
        asset_extensions=[".png"],
        folder_doc_filename="__doc__.md",
        input_dir_suffix=".inputs",
        output_dir_suffix=".outputs",
    )


def _base_config(
    tmp_path: Path,
    examples: ExamplesConfig | None,
) -> DocToolsConfig:
    return _make_config(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_examples=examples is not None,
        examples=examples,
    )


def test_generate_examples_docs_files_assets_and_nav(tmp_path: Path) -> None:
    """Examples generator writes docs, copies assets and updates nav."""
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()

    _ = (examples_dir / "hello.py").write_text("print('hello')\n", encoding="utf-8")
    _ = (examples_dir / "image.png").write_bytes(b"fake image")

    (tmp_path / "docs").mkdir()
    _ = (tmp_path / "mkdocs.yml").write_text(
        """
site_name: Demo
nav:
  - Examples:
    # --- AUTOGEN_EXAMPLES_START ---
    # --- AUTOGEN_EXAMPLES_END ---
""".lstrip(),
        encoding="utf-8",
    )

    cfg = _base_config(tmp_path, _examples_config(tmp_path, mode="file"))

    code = generate_examples_docs(cfg, Console())

    assert code == 0
    assert (tmp_path / "docs" / "examples" / "index.md").exists()
    assert (tmp_path / "docs" / "examples" / "hello.py.md").exists()
    assert (tmp_path / "docs" / "examples" / "image.png.md").exists()
    assert (tmp_path / "docs" / "examples" / "assets" / "image.png").exists()

    mkdocs_content = (tmp_path / "mkdocs.yml").read_text(encoding="utf-8")
    assert "Hello: examples/hello.py.md" in mkdocs_content


def test_generate_examples_docs_missing_source(tmp_path: Path) -> None:
    """Missing examples source is skipped gracefully."""
    cfg = _base_config(tmp_path, _examples_config(tmp_path, mode="file"))

    examples = cfg.examples
    assert examples is not None

    assert generate_examples_docs(cfg, Console()) == 0
    assert not examples.output_dir.exists()


def test_generate_examples_docs_without_mkdocs_file(tmp_path: Path) -> None:
    """Examples generation works even without mkdocs.yml."""
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    _ = (examples_dir / "demo.txt").write_text("hello\n", encoding="utf-8")

    cfg = _base_config(tmp_path, _examples_config(tmp_path, mode="file"))

    assert generate_examples_docs(cfg, Console()) == 0
    assert (tmp_path / "docs" / "examples" / "demo.txt.md").exists()


def test_generate_examples_docs_skips_configured_files(tmp_path: Path) -> None:
    """Examples generator respects skip dirs and files."""
    examples_dir = tmp_path / "examples"
    ignored_dir = examples_dir / "ignored"
    examples_dir.mkdir()
    ignored_dir.mkdir()

    _ = (examples_dir / "skip.py").write_text("print('skip')\n", encoding="utf-8")
    _ = (ignored_dir / "ignored.py").write_text("print('ignored')\n", encoding="utf-8")

    cfg = _base_config(tmp_path, _examples_config(tmp_path, mode="file"))

    assert generate_examples_docs(cfg, Console()) == 0
    assert not (tmp_path / "docs" / "examples" / "skip.py.md").exists()
    assert not (tmp_path / "docs" / "examples" / "ignored" / "ignored.py.md").exists()


def test_generate_examples_docs_asset_without_preview(tmp_path: Path) -> None:
    """Asset files can be rendered as normal file pages when previews are disabled."""
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    _ = (examples_dir / "image.png").write_bytes(b"fake image")

    examples_cfg = _examples_config(tmp_path, mode="file")
    examples_cfg = _make_examples_config(
        source_dir=examples_cfg.source_dir,
        output_dir=examples_cfg.output_dir,
        assets_dir=examples_cfg.assets_dir,
        mode="file",
        nav_start_marker=examples_cfg.nav_start_marker,
        nav_end_marker=examples_cfg.nav_end_marker,
        overview_enabled=False,
        copy_assets=False,
        show_image_previews=False,
        preview_max_width_px=PREVIEW_MAX_WIDTH,
        clean_output_dir=True,
        skip_dirs=[],
        skip_files=[],
        asset_extensions=[".png"],
        folder_doc_filename=examples_cfg.folder_doc_filename,
        input_dir_suffix=examples_cfg.input_dir_suffix,
        output_dir_suffix=examples_cfg.output_dir_suffix,
    )

    cfg = _base_config(tmp_path, examples_cfg)

    assert generate_examples_docs(cfg, Console()) == 0
    assert (tmp_path / "docs" / "examples" / "image.png.md").exists()
    assert not (tmp_path / "docs" / "examples" / "assets" / "image.png").exists()


def test_generate_examples_docs_missing_config(tmp_path: Path) -> None:
    """Missing examples config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="examples"):
        _ = generate_examples_docs(cfg, Console())


def test_generate_examples_docs_preserves_folder_tree(tmp_path: Path) -> None:
    """Examples navigation preserves source folder hierarchy."""
    examples_dir = tmp_path / "examples"
    first_dir = examples_dir / "01"
    second_dir = examples_dir / "02"

    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)

    _ = (first_dir / "ping.py").write_text("print('ping')\n", encoding="utf-8")
    _ = (first_dir / "result.txt").write_text("pong\n", encoding="utf-8")
    _ = (second_dir / "ExampleStartStop.mod").write_text(
        "MODULE ExampleStartStop\nENDMODULE\n",
        encoding="utf-8",
    )
    _ = (second_dir / "ExampleStartStop.pgf").write_text(
        "ExampleStartStop\n",
        encoding="utf-8",
    )

    (tmp_path / "docs").mkdir()
    _ = (tmp_path / "mkdocs.yml").write_text(
        """
site_name: Demo
nav:
  - Examples:
      # --- AUTOGEN_EXAMPLES_START ---
      - Old: old.md
      # --- AUTOGEN_EXAMPLES_END ---
""".lstrip(),
        encoding="utf-8",
    )

    cfg = _base_config(tmp_path, _examples_config(tmp_path, mode="file"))

    assert generate_examples_docs(cfg, Console()) == 0

    mkdocs_content = (tmp_path / "mkdocs.yml").read_text(encoding="utf-8")

    assert "- Old: old.md" not in mkdocs_content
    assert "- 01:" in mkdocs_content
    assert "- Ping: examples/01/ping.py.md" in mkdocs_content
    assert "- Result: examples/01/result.txt.md" in mkdocs_content
    assert "- 02:" in mkdocs_content
    assert "- Examplestartstop Mod: examples/02/ExampleStartStop.mod.md" in (
        mkdocs_content
    )
    assert "- Examplestartstop Pgf: examples/02/ExampleStartStop.pgf.md" in (
        mkdocs_content
    )

    assert (tmp_path / "docs" / "examples" / "01" / "ping.py.md").exists()
    assert (tmp_path / "docs" / "examples" / "01" / "result.txt.md").exists()
    assert (tmp_path / "docs" / "examples" / "02" / "ExampleStartStop.mod.md").exists()
    assert (tmp_path / "docs" / "examples" / "02" / "ExampleStartStop.pgf.md").exists()


def test_generate_examples_docs_directory_mode_uses_folder_doc_as_description(
    tmp_path: Path,
) -> None:
    """Directory mode uses __doc__.md as page content but does not expose it."""
    example_dir = tmp_path / "examples" / "trajectory" / "ik" / "kuka_dls_circle"
    example_dir.mkdir(parents=True)

    _ = (example_dir / "__doc__.md").write_text(
        "This example demonstrates DLS inverse kinematics.\n",
        encoding="utf-8",
    )
    _ = (example_dir / "kuka_dls_circle.py").write_text(
        "print('run kuka dls circle')\n",
        encoding="utf-8",
    )

    (tmp_path / "docs").mkdir()
    _ = (tmp_path / "mkdocs.yml").write_text(
        """
site_name: Demo
nav:
  - Examples:
      # --- AUTOGEN_EXAMPLES_START ---
      # --- AUTOGEN_EXAMPLES_END ---
""".lstrip(),
        encoding="utf-8",
    )

    cfg = _base_config(tmp_path, _examples_config(tmp_path))

    assert generate_examples_docs(cfg, Console()) == 0

    page = tmp_path / "docs" / "examples" / "trajectory" / "ik" / "kuka_dls_circle.md"
    assert page.exists()

    page_content = page.read_text(encoding="utf-8")
    assert "## Description" in page_content
    assert "This example demonstrates DLS inverse kinematics." in page_content
    assert "## Main script" in page_content
    assert "python examples/trajectory/ik/kuka_dls_circle/kuka_dls_circle.py" in (
        page_content
    )

    assert not (
        tmp_path
        / "docs"
        / "examples"
        / "trajectory"
        / "ik"
        / "kuka_dls_circle"
        / "__doc__.md"
    ).exists()

    mkdocs_content = (tmp_path / "mkdocs.yml").read_text(encoding="utf-8")
    assert "__doc__" not in mkdocs_content
    assert ".py.md" not in mkdocs_content
    assert "Kuka Dls Circle: examples/trajectory/ik/kuka_dls_circle.md" in (
        mkdocs_content
    )


def test_generate_examples_docs_directory_mode_copies_inputs_outputs(
    tmp_path: Path,
) -> None:
    """Directory mode copies IO assets and renders relative download links."""
    example_dir = tmp_path / "examples" / "trajectory" / "ik" / "demo"
    input_dir = example_dir / "demo.inputs" / "configs"
    output_dir = example_dir / "demo.outputs" / "images"

    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    _ = (example_dir / "demo.py").write_text("print('demo')\n", encoding="utf-8")
    _ = (input_dir / "params.json").write_text('{"gain": 1.0}\n', encoding="utf-8")
    _ = (output_dir / "result.png").write_bytes(b"fake image")

    cfg = _base_config(tmp_path, _examples_config(tmp_path))

    assert generate_examples_docs(cfg, Console()) == 0

    page = tmp_path / "docs" / "examples" / "trajectory" / "ik" / "demo.md"
    assert page.exists()

    copied_input = (
        tmp_path
        / "docs"
        / "examples"
        / "assets"
        / "trajectory"
        / "ik"
        / "demo"
        / "inputs"
        / "configs"
        / "params.json"
    )
    copied_output = (
        tmp_path
        / "docs"
        / "examples"
        / "assets"
        / "trajectory"
        / "ik"
        / "demo"
        / "outputs"
        / "images"
        / "result.png"
    )

    assert copied_input.exists()
    assert copied_output.exists()

    content = page.read_text(encoding="utf-8")
    assert "## Inputs" in content
    assert "## Outputs" in content
    expected_input_link = "".join(
        [
            "[`params.json`]",
            "(../../assets/trajectory/ik/demo/inputs/configs/params.json)",
        ],
    )
    expected_output_link = "".join(
        [
            "[`result.png`]",
            "(../../assets/trajectory/ik/demo/outputs/images/result.png)",
        ],
    )
    expected_preview = "".join(
        [
            '<img src="',
            "../../assets/trajectory/ik/demo/outputs/images/result.png",
            '"',
        ],
    )

    assert expected_input_link in content
    assert expected_output_link in content
    assert expected_preview in content


def test_generate_examples_docs_directory_mode_generates_overview_tree(
    tmp_path: Path,
) -> None:
    """Directory mode writes an overview with folder nodes and page links."""
    example_dir = tmp_path / "examples" / "trajectory" / "smm" / "synthetic"
    example_dir.mkdir(parents=True)

    synthetic_script = example_dir / "synthetic.py"
    _ = synthetic_script.write_text(
        "print('synthetic')\n",
        encoding="utf-8",
    )

    cfg = _base_config(tmp_path, _examples_config(tmp_path))

    assert generate_examples_docs(cfg, Console()) == 0

    overview = tmp_path / "docs" / "examples" / "index.md"
    assert overview.exists()

    content = overview.read_text(encoding="utf-8")
    assert "- 📂 **Trajectory**" in content
    assert "- 📂 **Smm**" in content
    assert "- 📃 [Synthetic](trajectory/smm/synthetic.md)" in content


def test_generate_examples_docs_rejects_unknown_examples_mode(tmp_path: Path) -> None:
    """Invalid examples generation modes fail explicitly."""
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()

    examples_cfg = _examples_config(tmp_path, mode="invalid")
    cfg = _base_config(tmp_path, examples_cfg)

    with pytest.raises(ValueError, match="Unsupported examples generation mode"):
        _ = generate_examples_docs(cfg, Console())
