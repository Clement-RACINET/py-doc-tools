"""Examples documentation generator."""

from __future__ import annotations

import fnmatch
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.markers import replace_between_markers
from py_doc_tools.core.titles import human_title

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig, ExamplesConfig
    from py_doc_tools.core.console import Console


type NavTree = dict[str, "NavTree | str"]


@dataclass(frozen=True)
class ExamplePage:
    """Generated documentation page for one example file."""

    source_file: Path
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

    _prepare_examples_output(examples_cfg)
    _write_overview_if_enabled(examples_cfg)

    pages = _generate_example_pages(
        cfg=cfg,
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


def _prepare_examples_output(examples_cfg: ExamplesConfig) -> None:
    """Prepare examples output directory."""
    if examples_cfg.clean_output_dir and examples_cfg.output_dir.exists():
        shutil.rmtree(examples_cfg.output_dir)

    examples_cfg.output_dir.mkdir(parents=True, exist_ok=True)


def _write_overview_if_enabled(examples_cfg: ExamplesConfig) -> None:
    """Write examples overview page when enabled."""
    if not examples_cfg.overview_enabled:
        return

    overview_path = examples_cfg.output_dir / "index.md"
    _ = overview_path.write_text(
        "# Examples\n\nGenerated examples documentation.\n",
        encoding="utf-8",
    )


def _generate_example_pages(
    *,
    cfg: DocToolsConfig,
    examples_cfg: ExamplesConfig,
) -> list[ExamplePage]:
    """Generate Markdown pages for all example files."""
    pages: list[ExamplePage] = []

    for file_path in sorted(examples_cfg.source_dir.rglob("*")):
        page = _generate_example_page(
            cfg=cfg,
            examples_cfg=examples_cfg,
            file_path=file_path,
        )

        if page is not None:
            pages.append(page)

    return pages


def _generate_example_page(
    *,
    cfg: DocToolsConfig,
    examples_cfg: ExamplesConfig,
    file_path: Path,
) -> ExamplePage | None:
    """Generate Markdown page for one example file."""
    if not file_path.is_file():
        return None

    if _should_skip(
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

    _write_example_content(
        file_path=file_path,
        output_file=output_file,
        title=title,
        examples_cfg=examples_cfg,
    )

    nav_path = output_file.relative_to(cfg.docs_src_dir).as_posix()

    return ExamplePage(
        source_file=file_path,
        relative_source=relative,
        output_file=output_file,
        nav_path=nav_path,
        title=title,
    )


def _write_example_content(
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
        _copy_asset(
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

    _ = output_file.write_text(markdown, encoding="utf-8")


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

    _ = context.output_file.write_text(markdown, encoding="utf-8")


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


def _build_examples_nav_tree(pages: list[ExamplePage]) -> NavTree:
    """Build a nested navigation tree from generated example pages."""
    tree: NavTree = {}

    for page in pages:
        current = tree

        for folder in page.relative_source.parts[:-1]:
            next_node = current.setdefault(folder, {})
            if isinstance(next_node, str):
                continue

            current = next_node

        current[page.title] = page.nav_path

    return tree


def _render_nav_tree(tree: NavTree, *, indent: int = 0) -> list[str]:
    """Render a nested navigation tree as MkDocs YAML lines."""
    lines: list[str] = []
    prefix = "  " * indent

    for label, value in tree.items():
        if isinstance(value, str):
            lines.append(f"{prefix}- {label}: {value}")
        else:
            lines.append(f"{prefix}- {label}:")
            lines.extend(_render_nav_tree(value, indent=indent + 1))

    return lines


def _title_for_example_file(file_path: Path) -> str:
    """Return a readable and collision-safe title for an example file."""
    suffix = file_path.suffix.lower()
    title = human_title(file_path.stem)

    if suffix in {".mod", ".pgf"}:
        suffix_label = suffix.removeprefix(".").title()
        return f"{title} {suffix_label}"

    return title


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
        ".mod": "rapid",
        ".pgf": "text",
    }

    return mapping.get(suffix.lower(), "text")
