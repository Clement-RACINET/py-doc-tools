"""Examples documentation generator."""

from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.markers import replace_between_markers
from py_doc_tools.core.titles import human_title

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


def generate_examples_docs(cfg: DocToolsConfig, console: Console) -> int:
    """Generate Markdown documentation pages for example files."""
    if cfg.examples is None:
        msg = "examples"
        raise MissingConfigSectionError(msg)

    examples_cfg = cfg.examples

    if not examples_cfg.source_dir.exists():
        console.warn(
            f"Examples source directory not found: {examples_cfg.source_dir}",
        )
        return 0

    examples_cfg.output_dir.mkdir(parents=True, exist_ok=True)

    nav_lines: list[str] = []

    if examples_cfg.overview_enabled:
        overview_path = examples_cfg.output_dir / "index.md"
        _ = overview_path.write_text(
            "# Examples\n\nGenerated examples documentation.\n",
            encoding="utf-8",
        )
        nav_lines.append("- Overview: examples/index.md")

    for file_path in sorted(examples_cfg.source_dir.rglob("*")):
        if not file_path.is_file():
            continue

        if _should_skip(
            file_path=file_path,
            source_root=examples_cfg.source_dir,
            skip_dirs=examples_cfg.skip_dirs,
            skip_files=examples_cfg.skip_files,
        ):
            continue

        relative = file_path.relative_to(examples_cfg.source_dir)
        output_file = examples_cfg.output_dir / relative.with_suffix(".md")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if file_path.suffix.lower() in examples_cfg.asset_extensions:
            if examples_cfg.copy_assets:
                _copy_asset(
                    file_path=file_path,
                    assets_dir=examples_cfg.assets_dir,
                    source_root=examples_cfg.source_dir,
                )

            if examples_cfg.show_image_previews:
                _write_image_page(
                    file_path=file_path,
                    source_root=examples_cfg.source_dir,
                    output_file=output_file,
                    assets_dir=examples_cfg.assets_dir,
                    max_width=examples_cfg.preview_max_width_px,
                )
            else:
                _write_file_page(file_path, output_file)
        else:
            _write_file_page(file_path, output_file)

        nav_path = output_file.relative_to(cfg.docs_src_dir).as_posix()
        nav_lines.append(f"- {human_title(file_path.stem)}: {nav_path}")

    if cfg.mkdocs_config.exists():
        replace_between_markers(
            file_path=cfg.mkdocs_config,
            start_marker=examples_cfg.nav_start_marker,
            end_marker=examples_cfg.nav_end_marker,
            new_block="\n".join(nav_lines),
        )

    console.ok(f"Examples documentation generated: {examples_cfg.output_dir}")
    return 0


def _write_file_page(file_path: Path, output_file: Path) -> None:
    language = _language_from_suffix(file_path.suffix)
    content = file_path.read_text(encoding="utf-8", errors="replace")
    title = human_title(file_path.stem)

    markdown = "\n".join(
        [
            f"# {title}",
            "",
            f"Source file: `{file_path.name}`",
            "",
            f"```{language}",
            content,
            "```",
            "",
        ],
    )

    _ = output_file.write_text(markdown, encoding="utf-8")


def _write_image_page(
    *,
    file_path: Path,
    source_root: Path,
    output_file: Path,
    assets_dir: Path,
    max_width: int,
) -> None:
    relative = file_path.relative_to(source_root)
    asset_path = assets_dir / relative
    image_relative = Path("assets") / relative
    title = human_title(file_path.stem)

    markdown = "\n".join(
        [
            f"# {title}",
            "",
            (
                f'<img src="../{image_relative.as_posix()}" '
                f'alt="{file_path.stem}" width="{max_width}">'
            ),
            "",
            f"Asset: `{asset_path.name}`",
            "",
        ],
    )

    _ = output_file.write_text(markdown, encoding="utf-8")


def _copy_asset(
    *,
    file_path: Path,
    assets_dir: Path,
    source_root: Path,
) -> None:
    relative = file_path.relative_to(source_root)
    destination = assets_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ = shutil.copy2(file_path, destination)


def _should_skip(
    *,
    file_path: Path,
    source_root: Path,
    skip_dirs: list[str],
    skip_files: list[str],
) -> bool:
    relative_parts = file_path.relative_to(source_root).parts

    for part in relative_parts[:-1]:
        if part in skip_dirs:
            return True

    return any(fnmatch.fnmatch(file_path.name, pattern) for pattern in skip_files)


def _language_from_suffix(suffix: str) -> str:
    mapping = {
        ".py": "python",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".md": "markdown",
        ".txt": "text",
        ".sh": "bash",
        ".ps1": "powershell",
    }

    return mapping.get(suffix.lower(), "text")
