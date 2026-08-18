"""Examples documentation generator."""

from __future__ import annotations

import fnmatch
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.markers import replace_between_markers
from py_doc_tools.core.titles import human_title

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig, ExamplesConfig
    from py_doc_tools.core.console import Console


type NavTree = dict[str, "NavTree | str"]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}

FILE_EMOJI_BY_EXTENSION = {
    ".json": "🧩",
    ".csv": "📊",
    ".pdf": "📕",
    ".txt": "📝",
    ".log": "📝",
    ".zip": "🗜️",
    ".tar": "🗜️",
    ".gz": "🗜️",
    ".7z": "🗜️",
    ".xlsx": "📗",
    ".xls": "📗",
}


@dataclass(frozen=True)
class ExamplePage:
    """Generated documentation page for one example item.

    In ``file`` mode, the source path is a file.
    In ``directory`` mode, the source path is an example directory.
    """

    source_path: Path
    relative_source: Path
    output_file: Path
    nav_path: str
    title: str


@dataclass(frozen=True)
class ImagePageContext:
    """Context required to generate an image documentation page."""

    file_path: Path
    source_root: Path
    output_file: Path
    assets_dir: Path
    max_width: int
    title: str


@dataclass(frozen=True)
class IoFile:
    """Input or output file collected from an example IO directory."""

    absolute_path: Path
    relative_inside_io_dir: str


@dataclass(frozen=True)
class DirectoryExampleContext:
    """Rendering context for one directory-mode example page."""

    cfg: DocToolsConfig
    examples_cfg: ExamplesConfig
    example_dir: Path
    output_file: Path
    title: str


@dataclass(frozen=True)
class IoSectionContext:
    """Rendering context for an input or output section."""

    cfg: DocToolsConfig
    examples_cfg: ExamplesConfig
    section_title: str
    empty_message: str
    intro_message: str
    io_kind: str
    files: list[IoFile]
    show_preview: bool
    relative_example: str
    docs_relative_output: str


@dataclass(frozen=True)
class AssetCopyContext:
    """Context used to copy an IO asset into the documentation tree."""

    src_file: Path
    rel_example_posix: str
    rel_inside_io_posix: str
    io_kind: str
    examples_cfg: ExamplesConfig
    docs_src_dir: Path


@dataclass
class FileTreeFile:
    """One file entry in an input/output tree."""

    name: str
    display: str
    url: str
    extension: str


@dataclass
class FileTreeNode:
    """Typed file tree node used to render downloadable files."""

    files: list[FileTreeFile] = field(default_factory=list)
    children: dict[str, FileTreeNode] = field(default_factory=dict)


@dataclass
class OverviewNode:
    """Typed overview tree node."""

    href: str | None = None
    title: str | None = None
    children: dict[str, OverviewNode] = field(default_factory=dict)


def generate_examples_docs(cfg: DocToolsConfig, console: Console) -> int:
    """Generate Markdown documentation pages for examples."""
    if cfg.examples is None:
        msg = "examples"
        raise MissingConfigSectionError(msg)

    examples_cfg = cfg.examples

    if not examples_cfg.source_dir.exists():
        console.warn(
            f"Examples source directory not found: {examples_cfg.source_dir}",
        )
        return 0

    _validate_examples_mode(examples_cfg.mode)
    _prepare_examples_output(examples_cfg)

    if examples_cfg.mode == "file":
        pages = _generate_file_mode_pages(
            cfg=cfg,
            examples_cfg=examples_cfg,
        )
    else:
        pages = _generate_directory_mode_pages(
            cfg=cfg,
            examples_cfg=examples_cfg,
        )

    _write_overview_if_enabled(
        pages=pages,
        examples_cfg=examples_cfg,
    )

    nav_block = _build_examples_nav_block(
        pages=pages,
        examples_cfg=examples_cfg,
        docs_src_dir=cfg.docs_src_dir,
    )

    if cfg.mkdocs_config.exists():
        replace_between_markers(
            file_path=cfg.mkdocs_config,
            start_marker=examples_cfg.nav_start_marker,
            end_marker=examples_cfg.nav_end_marker,
            new_block=nav_block,
            preserve_marker_indent=True,
        )

    console.ok(f"Examples documentation generated: {examples_cfg.output_dir}")
    return 0


def _validate_examples_mode(mode: str) -> None:
    """Validate the examples generation mode."""
    if mode not in {"directory", "file"}:
        msg = f"Unsupported examples generation mode: {mode!r}"
        raise ValueError(msg)


def _prepare_examples_output(examples_cfg: ExamplesConfig) -> None:
    """Prepare examples output directory."""
    if examples_cfg.clean_output_dir and examples_cfg.output_dir.exists():
        shutil.rmtree(examples_cfg.output_dir)

    examples_cfg.output_dir.mkdir(parents=True, exist_ok=True)

    if examples_cfg.copy_assets:
        examples_cfg.assets_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Directory mode
# =============================================================================


def _generate_directory_mode_pages(
    *,
    cfg: DocToolsConfig,
    examples_cfg: ExamplesConfig,
) -> list[ExamplePage]:
    """Generate one documentation page per example directory."""
    pages: list[ExamplePage] = []

    for example_dir in _iter_example_dirs(examples_cfg):
        page = _generate_directory_mode_page(
            cfg=cfg,
            examples_cfg=examples_cfg,
            example_dir=example_dir,
        )
        pages.append(page)

    return pages


def _iter_example_dirs(examples_cfg: ExamplesConfig) -> list[Path]:
    """Return all example directories in deterministic order."""
    candidates: list[Path] = []

    for current, dirs, _files in os.walk(examples_cfg.source_dir):
        dirs[:] = [
            dirname
            for dirname in dirs
            if dirname not in examples_cfg.skip_dirs
            and not _matches_any(dirname, examples_cfg.skip_dirs)
        ]

        current_path = Path(current)

        if _is_example_dir(current_path, examples_cfg):
            candidates.append(current_path)

    return sorted(candidates, key=lambda path: path.as_posix().lower())


def _is_example_dir(example_dir: Path, examples_cfg: ExamplesConfig) -> bool:
    """Return whether a directory should produce an example page."""
    if not example_dir.is_dir():
        return False

    if _find_main_script(example_dir, examples_cfg) is not None:
        return True

    return _has_direct_io_dir(
        example_dir,
        examples_cfg.input_dir_suffix,
    ) or _has_direct_io_dir(
        example_dir,
        examples_cfg.output_dir_suffix,
    )


def _has_direct_io_dir(example_dir: Path, suffix: str) -> bool:
    """Return whether the example directory has a direct IO subdirectory."""
    return any(
        child.is_dir() and child.name.endswith(suffix)
        for child in example_dir.iterdir()
    )


def _generate_directory_mode_page(
    *,
    cfg: DocToolsConfig,
    examples_cfg: ExamplesConfig,
    example_dir: Path,
) -> ExamplePage:
    """Generate one rich documentation page for an example directory."""
    relative_dir = example_dir.relative_to(examples_cfg.source_dir)
    output_file = examples_cfg.output_dir / relative_dir.with_suffix(".md")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    title = human_title(example_dir.name)
    nav_path = output_file.relative_to(cfg.docs_src_dir).as_posix()

    context = DirectoryExampleContext(
        cfg=cfg,
        examples_cfg=examples_cfg,
        example_dir=example_dir,
        output_file=output_file,
        title=title,
    )
    markdown = _build_directory_example_markdown(context)

    _ = output_file.write_text(markdown, encoding="utf-8", newline="\n")

    return ExamplePage(
        source_path=example_dir,
        relative_source=relative_dir,
        output_file=output_file,
        nav_path=nav_path,
        title=title,
    )


def _build_directory_example_markdown(context: DirectoryExampleContext) -> str:
    """Build Markdown content for one example directory."""
    relative_example = context.example_dir.relative_to(
        context.examples_cfg.source_dir,
    ).as_posix()
    docs_relative_output = context.output_file.relative_to(
        context.cfg.docs_src_dir,
    ).as_posix()

    main_script = _find_main_script(context.example_dir, context.examples_cfg)
    scripts = _list_python_scripts(context.example_dir, context.examples_cfg)
    inputs = _collect_io_files(
        example_dir=context.example_dir,
        suffix=context.examples_cfg.input_dir_suffix,
        examples_cfg=context.examples_cfg,
    )
    outputs = _collect_io_files(
        example_dir=context.example_dir,
        suffix=context.examples_cfg.output_dir_suffix,
        examples_cfg=context.examples_cfg,
    )

    lines: list[str] = [
        f"# 📃 {context.title}",
        "",
        f"**Source folder**: `examples/{relative_example}`",
        "",
    ]

    _append_folder_description(
        lines=lines,
        example_dir=context.example_dir,
        examples_cfg=context.examples_cfg,
    )

    _append_scripts_section(
        lines=lines,
        relative_example=relative_example,
        scripts=scripts,
        main_script=main_script,
    )

    _append_io_section(
        lines=lines,
        context=IoSectionContext(
            cfg=context.cfg,
            examples_cfg=context.examples_cfg,
            section_title="Inputs",
            empty_message="- No input file detected (`*.inputs/`).",
            intro_message=(
                "> Input files available for download. Inline preview is disabled "
                "for inputs."
            ),
            io_kind="inputs",
            files=inputs,
            show_preview=False,
            relative_example=relative_example,
            docs_relative_output=docs_relative_output,
        ),
    )

    _append_io_section(
        lines=lines,
        context=IoSectionContext(
            cfg=context.cfg,
            examples_cfg=context.examples_cfg,
            section_title="Outputs",
            empty_message="- No output file detected (`*.outputs/`).",
            intro_message=(
                "> Images are displayed as reduced previews below each file."
            ),
            io_kind="outputs",
            files=outputs,
            show_preview=context.examples_cfg.show_image_previews,
            relative_example=relative_example,
            docs_relative_output=docs_relative_output,
        ),
    )

    return "\n".join(lines).rstrip() + "\n"


def _append_folder_description(
    *,
    lines: list[str],
    example_dir: Path,
    examples_cfg: ExamplesConfig,
) -> None:
    """Append the optional folder documentation section."""
    doc_file = example_dir / examples_cfg.folder_doc_filename

    if not doc_file.exists() or not doc_file.is_file():
        return

    content = doc_file.read_text(encoding="utf-8", errors="replace").strip()

    if not content:
        return

    lines.extend(
        [
            "## Description",
            "",
            content,
            "",
        ],
    )


def _append_scripts_section(
    *,
    lines: list[str],
    relative_example: str,
    scripts: list[Path],
    main_script: Path | None,
) -> None:
    """Append scripts and execution details."""
    lines.extend(["## Scripts", ""])

    if scripts:
        for script in scripts:
            marker = " *(main)*" if main_script == script else ""
            lines.append(f"- `{script.name}`{marker}")
    else:
        lines.append("- No Python script detected in this folder.")

    lines.append("")

    if main_script is None:
        lines.extend(
            [
                "## Execution",
                "",
                "```bash",
                f"# Add a script in examples/{relative_example}",
                "```",
                "",
            ],
        )
        return

    rel_script = f"examples/{relative_example}/{main_script.name}"
    code = main_script.read_text(encoding="utf-8", errors="replace")

    lines.extend(
        [
            "## Main script",
            "",
            f"`{rel_script}`",
            "",
            "```python",
            code.rstrip(),
            "```",
            "",
            "## Execution",
            "",
            "```bash",
            f"python {rel_script}",
            "```",
            "",
        ],
    )


def _append_io_section(
    *,
    lines: list[str],
    context: IoSectionContext,
) -> None:
    """Append an input or output file tree section."""
    lines.extend([f"## {context.section_title}", ""])

    if not context.files:
        lines.extend([context.empty_message, ""])
        return

    lines.extend([context.intro_message, "", "### Downloadable files", ""])

    file_items: list[tuple[str, str, str]] = []

    for file_item in context.files:
        asset_rel = _copy_io_asset_preserve_tree(
            AssetCopyContext(
                src_file=file_item.absolute_path,
                rel_example_posix=context.relative_example,
                rel_inside_io_posix=file_item.relative_inside_io_dir,
                io_kind=context.io_kind,
                examples_cfg=context.examples_cfg,
                docs_src_dir=context.cfg.docs_src_dir,
            ),
        )

        asset_url = _markdown_asset_link_from_docs_src_rel(
            asset_rel_from_docs_src=asset_rel,
            md_rel_from_docs_src=context.docs_relative_output,
            docs_src_dir=context.cfg.docs_src_dir,
        )

        file_items.append(
            (
                file_item.relative_inside_io_dir,
                asset_url,
                file_item.absolute_path.suffix.lower(),
            ),
        )

    _emit_download_tree_markdown(
        lines=lines,
        node=_build_file_tree(file_items),
        level=0,
        show_preview=context.show_preview,
        examples_cfg=context.examples_cfg,
    )

    lines.append("")


def _find_main_script(
    example_dir: Path,
    examples_cfg: ExamplesConfig,
) -> Path | None:
    """Find the main Python script for an example directory.

    Preference order:
        1. A script named exactly like the example directory.
        2. The first Python file sorted alphabetically.
    """
    scripts = _list_python_scripts(example_dir, examples_cfg)

    if not scripts:
        return None

    expected = example_dir / f"{example_dir.name}.py"
    return expected if expected in scripts else scripts[0]


def _list_python_scripts(
    example_dir: Path,
    examples_cfg: ExamplesConfig,
) -> list[Path]:
    """List direct Python scripts in an example directory."""
    scripts = [
        child
        for child in example_dir.iterdir()
        if child.is_file()
        and child.suffix == ".py"
        and child.name != "__init__.py"
        and not _matches_any(child.name, examples_cfg.skip_files)
    ]

    return sorted(scripts, key=lambda path: path.name.lower())


def _collect_io_files(
    *,
    example_dir: Path,
    suffix: str,
    examples_cfg: ExamplesConfig,
) -> list[IoFile]:
    """Collect files from direct IO directories of one example directory."""
    items: list[IoFile] = []

    io_dirs = sorted(
        [
            child
            for child in example_dir.iterdir()
            if child.is_dir() and child.name.endswith(suffix)
        ],
        key=lambda path: path.name.lower(),
    )

    for io_dir in io_dirs:
        for current, dirs, files in os.walk(io_dir):
            dirs[:] = [
                dirname
                for dirname in dirs
                if dirname not in examples_cfg.skip_dirs
                and not _matches_any(dirname, examples_cfg.skip_dirs)
            ]

            current_path = Path(current)

            for filename in sorted(files, key=str.lower):
                if _matches_any(filename, examples_cfg.skip_files):
                    continue

                absolute_file = current_path / filename
                relative_inside = absolute_file.relative_to(io_dir).as_posix()

                items.append(
                    IoFile(
                        absolute_path=absolute_file,
                        relative_inside_io_dir=relative_inside,
                    ),
                )

    return sorted(items, key=lambda item: item.relative_inside_io_dir.lower())


def _copy_io_asset_preserve_tree(context: AssetCopyContext) -> str:
    """Copy an IO asset while preserving the example-relative tree.

    Returns:
        The copied asset path relative to ``docs_src_dir``.
    """
    if not context.examples_cfg.copy_assets:
        return context.src_file.as_posix()

    destination = (
        context.examples_cfg.assets_dir
        / context.rel_example_posix
        / context.io_kind
        / Path(context.rel_inside_io_posix)
    )

    destination.parent.mkdir(parents=True, exist_ok=True)

    final_destination = _non_conflicting_destination(
        src_file=context.src_file,
        destination=destination,
    )

    _ = shutil.copy2(context.src_file, final_destination)

    return final_destination.relative_to(context.docs_src_dir).as_posix()


def _non_conflicting_destination(
    *,
    src_file: Path,
    destination: Path,
) -> Path:
    """Return a non-conflicting destination path for an asset copy."""
    if not destination.exists():
        return destination

    if src_file.read_bytes() == destination.read_bytes():
        return destination

    base = destination.with_suffix("")
    extension = destination.suffix
    index = 2

    while True:
        candidate = Path(f"{base}_{index}{extension}")

        if not candidate.exists():
            return candidate

        index += 1


def _markdown_asset_link_from_docs_src_rel(
    *,
    asset_rel_from_docs_src: str,
    md_rel_from_docs_src: str,
    docs_src_dir: Path,
) -> str:
    """Build a Markdown-safe relative link from a page to an asset."""
    asset_abs = docs_src_dir / Path(asset_rel_from_docs_src)
    md_abs = docs_src_dir / Path(md_rel_from_docs_src)

    relative_link = os.path.relpath(asset_abs, start=md_abs.parent)
    return relative_link.replace(os.sep, "/")


def _build_file_tree(file_items: list[tuple[str, str, str]]) -> FileTreeNode:
    """Build a nested file tree from flat file items."""
    root = FileTreeNode()

    for display_name, asset_url, extension in file_items:
        parts = display_name.split("/")
        cursor = root

        for part in parts[:-1]:
            if part not in cursor.children:
                cursor.children[part] = FileTreeNode()
            cursor = cursor.children[part]

        cursor.files.append(
            FileTreeFile(
                name=parts[-1],
                display=display_name,
                url=asset_url,
                extension=extension.lower(),
            ),
        )

    return root


def _emit_download_tree_markdown(
    *,
    lines: list[str],
    node: FileTreeNode,
    level: int,
    show_preview: bool,
    examples_cfg: ExamplesConfig,
) -> None:
    """Append a Markdown download tree to the given lines."""
    pad = "    " * level

    for dirname in sorted(node.children, key=str.lower):
        lines.append(f"{pad}- 📂 **{dirname}**")
        _emit_download_tree_markdown(
            lines=lines,
            node=node.children[dirname],
            level=level + 1,
            show_preview=show_preview,
            examples_cfg=examples_cfg,
        )

    for file_info in sorted(node.files, key=lambda item: item.name.lower()):
        file_link = "".join(
            [
                f"{pad}- {_file_emoji(file_info.name)} ",
                f"[`{file_info.name}`]({file_info.url})",
            ],
        )
        lines.append(file_link)

        if show_preview and file_info.extension in IMAGE_EXTENSIONS:
            preview_pad = "    " * (level + 1)
            style = "".join(
                [
                    "display:block; ",
                    f"max-width: {examples_cfg.preview_max_width_px}px; ",
                    "width: 100%; ",
                    "height: auto; ",
                    "border: 1px solid #ddd; ",
                    "border-radius: 8px; ",
                    "margin-top: 6px;",
                ],
            )
            image_html = "".join(
                [
                    f'{preview_pad}<img src="{file_info.url}" ',
                    f'alt="{file_info.display}" style="{style}" />',
                ],
            )

            lines.append(f"{preview_pad}<br>")
            lines.append(image_html)


def _file_emoji(file_name: str) -> str:
    """Return a small emoji based on the file extension."""
    extension = Path(file_name).suffix.lower()

    if extension in IMAGE_EXTENSIONS:
        return "🖼️"

    return FILE_EMOJI_BY_EXTENSION.get(extension, "📄")


# =============================================================================
# File mode, kept for backward compatibility
# =============================================================================


def _generate_file_mode_pages(
    *,
    cfg: DocToolsConfig,
    examples_cfg: ExamplesConfig,
) -> list[ExamplePage]:
    """Generate Markdown pages for all example files."""
    pages: list[ExamplePage] = []

    for file_path in sorted(examples_cfg.source_dir.rglob("*")):
        page = _generate_file_mode_page(
            cfg=cfg,
            examples_cfg=examples_cfg,
            file_path=file_path,
        )

        if page is not None:
            pages.append(page)

    return pages


def _generate_file_mode_page(
    *,
    cfg: DocToolsConfig,
    examples_cfg: ExamplesConfig,
    file_path: Path,
) -> ExamplePage | None:
    """Generate Markdown page for one example file."""
    if not file_path.is_file():
        return None

    if _should_skip_file_mode(
        file_path=file_path,
        source_root=examples_cfg.source_dir,
        skip_dirs=examples_cfg.skip_dirs,
        skip_files=examples_cfg.skip_files,
    ):
        return None

    relative = file_path.relative_to(examples_cfg.source_dir)
    output_file = examples_cfg.output_dir / _markdown_output_path(relative)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    title = _title_for_example_file(file_path)

    _write_file_mode_content(
        file_path=file_path,
        output_file=output_file,
        title=title,
        examples_cfg=examples_cfg,
    )

    nav_path = output_file.relative_to(cfg.docs_src_dir).as_posix()

    return ExamplePage(
        source_path=file_path,
        relative_source=relative,
        output_file=output_file,
        nav_path=nav_path,
        title=title,
    )


def _write_file_mode_content(
    *,
    file_path: Path,
    output_file: Path,
    title: str,
    examples_cfg: ExamplesConfig,
) -> None:
    """Write the correct documentation page type for one example file."""
    if file_path.suffix.lower() not in examples_cfg.asset_extensions:
        _write_file_page(
            file_path=file_path,
            output_file=output_file,
            title=title,
        )
        return

    if examples_cfg.copy_assets:
        _copy_file_mode_asset(
            file_path=file_path,
            assets_dir=examples_cfg.assets_dir,
            source_root=examples_cfg.source_dir,
        )

    if not examples_cfg.show_image_previews:
        _write_file_page(
            file_path=file_path,
            output_file=output_file,
            title=title,
        )
        return

    context = ImagePageContext(
        file_path=file_path,
        source_root=examples_cfg.source_dir,
        output_file=output_file,
        assets_dir=examples_cfg.assets_dir,
        max_width=examples_cfg.preview_max_width_px,
        title=title,
    )

    _write_image_page(context)


def _markdown_output_path(relative_source: Path) -> Path:
    """Return the Markdown output path for an example source file.

    The original file extension is preserved in the generated Markdown filename
    to avoid collisions.

    Examples:
        ExampleStartStop.mod -> ExampleStartStop.mod.md
        ExampleStartStop.pgf -> ExampleStartStop.pgf.md
        ping.py -> ping.py.md
    """
    return relative_source.with_name(f"{relative_source.name}.md")


def _write_file_page(
    *,
    file_path: Path,
    output_file: Path,
    title: str,
) -> None:
    """Write a Markdown page displaying a source file."""
    language = _language_from_suffix(file_path.suffix)
    content = file_path.read_text(encoding="utf-8", errors="replace")

    markdown = "\n".join(
        [
            f"# {title}",
            "",
            f"Source file: `{file_path.name}`",
            "",
            f"```{language}",
            content.rstrip(),
            "```",
            "",
        ],
    )

    _ = output_file.write_text(markdown, encoding="utf-8", newline="\n")


def _write_image_page(context: ImagePageContext) -> None:
    """Write an image preview documentation page."""
    relative = context.file_path.relative_to(context.source_root)
    asset_path = context.assets_dir / relative
    image_relative = f"assets/{relative.as_posix()}"

    markdown = "\n".join(
        [
            f"# {context.title}",
            "",
            (
                f'<img src="../{image_relative}" '
                f'alt="{context.file_path.stem}" width="{context.max_width}">'
            ),
            "",
            f"Asset: `{asset_path.name}`",
            "",
        ],
    )

    _ = context.output_file.write_text(markdown, encoding="utf-8", newline="\n")


def _copy_file_mode_asset(
    *,
    file_path: Path,
    assets_dir: Path,
    source_root: Path,
) -> None:
    """Copy one asset in file mode."""
    relative = file_path.relative_to(source_root)
    destination = assets_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ = shutil.copy2(file_path, destination)


def _should_skip_file_mode(
    *,
    file_path: Path,
    source_root: Path,
    skip_dirs: list[str],
    skip_files: list[str],
) -> bool:
    """Return whether a file-mode page should be skipped."""
    relative_parts = file_path.relative_to(source_root).parts

    for part in relative_parts[:-1]:
        if part in skip_dirs or _matches_any(part, skip_dirs):
            return True

    return _matches_any(file_path.name, skip_files)


# =============================================================================
# Overview and navigation
# =============================================================================


def _write_overview_if_enabled(
    *,
    pages: list[ExamplePage],
    examples_cfg: ExamplesConfig,
) -> None:
    """Write the examples overview page when enabled."""
    if not examples_cfg.overview_enabled:
        return

    overview_path = examples_cfg.output_dir / "index.md"
    overview_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = ["# Examples", ""]

    if not pages:
        lines.extend(["No example page generated.", ""])
        _ = overview_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        return

    lines.append("Generated examples documentation.")
    lines.append("")

    overview_tree = _build_overview_tree(
        pages=pages,
        overview_path=overview_path,
    )

    _emit_overview_tree(lines=lines, node=overview_tree, level=0)
    lines.append("")

    _ = overview_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _build_overview_tree(
    *,
    pages: list[ExamplePage],
    overview_path: Path,
) -> OverviewNode:
    """Build a directory-like tree for the overview page."""
    root = OverviewNode()

    for page in pages:
        cursor = root

        for part in page.relative_source.parts:
            if part not in cursor.children:
                cursor.children[part] = OverviewNode()
            cursor = cursor.children[part]

        relative_link = os.path.relpath(page.output_file, start=overview_path.parent)
        cursor.href = relative_link.replace(os.sep, "/")
        cursor.title = page.title

    return root


def _emit_overview_tree(
    *,
    lines: list[str],
    node: OverviewNode,
    level: int,
) -> None:
    """Render an overview tree as Markdown bullets."""
    pad = "    " * level

    for name in sorted(node.children, key=str.lower):
        child = node.children[name]
        title = child.title or human_title(name)

        if child.children:
            lines.append(f"{pad}- 📂 **{human_title(name)}**")

            if child.href:
                lines.append(f"{pad}    - 📃 [{title}]({child.href})")

            _emit_overview_tree(lines=lines, node=child, level=level + 1)
            continue

        if child.href:
            lines.append(f"{pad}- 📃 [{title}]({child.href})")
        else:
            lines.append(f"{pad}- 📂 **{human_title(name)}**")


def _build_examples_nav_block(
    *,
    pages: list[ExamplePage],
    examples_cfg: ExamplesConfig,
    docs_src_dir: Path,
) -> str:
    """Build complete examples MkDocs navigation block."""
    nav_lines: list[str] = []

    if examples_cfg.overview_enabled:
        overview_file = examples_cfg.output_dir / "index.md"
        overview_nav_path = overview_file.relative_to(docs_src_dir).as_posix()
        nav_lines.append(f"- Overview: {overview_nav_path}")

    nav_tree = _build_examples_nav_tree(pages)
    nav_lines.extend(_render_nav_tree(nav_tree))

    return "\n".join(nav_lines)


def _build_examples_nav_tree(pages: list[ExamplePage]) -> NavTree:
    """Build a nested navigation tree from generated example pages."""
    tree: NavTree = {}

    for page in pages:
        current = tree

        for folder in page.relative_source.parts[:-1]:
            folder_title = human_title(folder)
            existing = current.get(folder_title)

            if isinstance(existing, str):
                continue

            if existing is None:
                existing = {}
                current[folder_title] = existing

            current = existing

        current[page.title] = page.nav_path

    return tree


def _render_nav_tree(tree: NavTree, *, indent: int = 0) -> list[str]:
    """Render a nested navigation tree as MkDocs YAML lines."""
    lines: list[str] = []
    prefix = "  " * indent

    for label in sorted(tree, key=str.lower):
        value = tree[label]

        if isinstance(value, str):
            lines.append(f"{prefix}- {label}: {value}")
        else:
            lines.append(f"{prefix}- {label}:")
            lines.extend(_render_nav_tree(value, indent=indent + 1))

    return lines


# =============================================================================
# Shared helpers
# =============================================================================


def _title_for_example_file(file_path: Path) -> str:
    """Return a readable and collision-safe title for an example file."""
    suffix = file_path.suffix.lower()
    title = human_title(file_path.stem)

    if suffix in {".mod", ".pgf"}:
        suffix_label = suffix.removeprefix(".").title()
        return f"{title} {suffix_label}"

    return title


def _matches_any(value: str, patterns: list[str]) -> bool:
    """Return whether a value matches at least one fnmatch pattern."""
    return any(fnmatch.fnmatch(value, pattern) for pattern in patterns)


def _language_from_suffix(suffix: str) -> str:
    """Return a Markdown code fence language for a file suffix."""
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
        ".mod": "rapid",
        ".pgf": "text",
    }

    return mapping.get(suffix.lower(), "text")
