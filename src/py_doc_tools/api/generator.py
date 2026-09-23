# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""API documentation generation."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.filesystem import ensure_dir, remove_dir, write_text
from py_doc_tools.core.titles import human_title

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import ApiConfig, DocToolsConfig
    from py_doc_tools.core.console import Console


@dataclass(slots=True)
class ApiGenerationContext:
    """Runtime context for API documentation generation."""

    cfg: DocToolsConfig
    api_cfg: ApiConfig
    console: Console
    overview_lines: list[str]

    def __init__(
        self,
        *,
        cfg: DocToolsConfig,
        api_cfg: ApiConfig,
        console: Console,
        overview_lines: list[str],
    ) -> None:
        """Initialize API generation context."""
        self.cfg = cfg
        self.api_cfg = api_cfg
        self.console = console
        self.overview_lines = overview_lines


def generate_api_docs(cfg: DocToolsConfig, console: Console) -> str:
    """Generate API Markdown pages and return a MkDocs nav block.

    Args:
        cfg: Root tool configuration.
        console: Console logger.

    Returns:
        Generated MkDocs navigation block.
    """
    if cfg.api is None:
        msg = "api"
        raise MissingConfigSectionError(msg)

    api_cfg = cfg.api

    if api_cfg.clean_output_dir:
        console.info(f"Cleaning API output directory: {api_cfg.output_dir}")
        remove_dir(api_cfg.output_dir)

    ensure_dir(api_cfg.output_dir)

    ctx = ApiGenerationContext(
        cfg=cfg,
        api_cfg=api_cfg,
        console=console,
        overview_lines=[
            "# API overview",
            "",
            "Automatically generated API documentation.",
            "",
        ],
    )

    nav_lines: list[str] = []

    if api_cfg.overview_enabled:
        overview_path = api_cfg.output_dir / "api_overview.md"
        overview_rel = _relative_to_docs_src(overview_path, cfg)
        nav_lines.append(
            _nav_line(
                indent=0,
                label="API overview",
                rel_path=overview_rel,
                use_emojis=cfg.use_emojis,
                kind="overview",
            ),
        )

    for package in cfg.packages:
        package_lines = _generate_package(package, ctx)

        if package_lines:
            nav_lines.append(
                _folder_line(
                    indent=0,
                    label=human_title(package),
                    use_emojis=cfg.use_emojis,
                ),
            )
            nav_lines.extend(package_lines)

    if api_cfg.overview_enabled:
        write_text(
            api_cfg.output_dir / "api_overview.md",
            "\n".join(ctx.overview_lines),
        )

    return "\n".join(nav_lines)


def _generate_package(package: str, ctx: ApiGenerationContext) -> list[str]:
    src_root = ctx.cfg.project_root / package
    dst_root = ctx.api_cfg.output_dir / package

    if not src_root.exists():
        ctx.console.warn(f"Package directory not found: {src_root}")
        return []

    ctx.console.info(f"Generating API pages for package: {package}")

    return _walk_package(
        src=src_root,
        dst=dst_root,
        indent=1,
        ctx=ctx,
    )


def _walk_package(
    *,
    src: Path,
    dst: Path,
    indent: int,
    ctx: ApiGenerationContext,
) -> list[str]:
    ensure_dir(dst)
    lines: list[str] = []

    if ctx.api_cfg.folder_intro_enabled:
        intro_line = _generate_folder_intro(src=src, dst=dst, ctx=ctx)
        lines.append(_indent_line(intro_line, indent))

    for py_file in _iter_python_files(src, ctx.api_cfg):
        module_line = _generate_module_page(py_file=py_file, dst=dst, ctx=ctx)
        lines.append(_indent_line(module_line, indent))

    for subdir in _iter_subdirs(src, ctx.api_cfg):
        sub_lines = _walk_package(
            src=subdir,
            dst=dst / subdir.name,
            indent=indent + 1,
            ctx=ctx,
        )

        if sub_lines:
            lines.append(
                _folder_line(
                    indent=indent,
                    label=human_title(subdir.name),
                    use_emojis=ctx.cfg.use_emojis,
                ),
            )
            lines.extend(sub_lines)

    return lines


def _generate_folder_intro(
    *,
    src: Path,
    dst: Path,
    ctx: ApiGenerationContext,
) -> str:
    intro_src = src / ctx.api_cfg.folder_intro_filename
    intro_dst = dst / f"{src.name}.md"

    content_parts = [f"# Intro {src.name}", ""]

    if intro_src.exists():
        content_parts.append(intro_src.read_text(encoding="utf-8").strip())
    else:
        content_parts.append(
            f"No description provided. Add `{ctx.api_cfg.folder_intro_filename}`.",
        )

    write_text(intro_dst, "\n".join(content_parts) + "\n")

    rel = _relative_to_docs_src(intro_dst, ctx.cfg)

    return _nav_line(
        indent=0,
        label=f"Intro {src.name}",
        rel_path=rel,
        use_emojis=ctx.cfg.use_emojis,
        kind="intro",
    )


def _generate_module_page(
    *,
    py_file: Path,
    dst: Path,
    ctx: ApiGenerationContext,
) -> str:
    module_name = py_file.stem
    module_path = _module_path(py_file, ctx.cfg.project_root)
    title = human_title(module_name)
    dst_md = dst / f"{module_name}.md"

    content = _render_module_page(
        py_file=py_file,
        module_path=module_path,
        title=title,
        api_cfg=ctx.api_cfg,
    )

    write_text(dst_md, content)

    rel = _relative_to_docs_src(dst_md, ctx.cfg)
    ctx.overview_lines.append(f"- [{title}]({rel})")
    ctx.console.debug(f"Generated {module_path} -> {rel}")

    return _nav_line(
        indent=0,
        label=title,
        rel_path=rel,
        use_emojis=ctx.cfg.use_emojis,
        kind="file",
    )


def _render_module_page(
    *,
    py_file: Path,
    module_path: str,
    title: str,
    api_cfg: ApiConfig,
) -> str:
    parts: list[str] = [f"# {title}", ""]

    pre = py_file.with_name(f"{py_file.stem}{api_cfg.module_pre_suffix}")
    post = py_file.with_name(f"{py_file.stem}{api_cfg.module_post_suffix}")

    if pre.exists():
        parts.extend([pre.read_text(encoding="utf-8").strip(), ""])

    parts.extend([f"::: {module_path}", ""])

    if post.exists():
        parts.extend([post.read_text(encoding="utf-8").strip(), ""])

    return "\n".join(parts)


def _iter_python_files(src: Path, api_cfg: ApiConfig) -> list[Path]:
    return sorted(
        [
            item
            for item in src.iterdir()
            if item.is_file()
            and item.suffix == ".py"
            and not _is_excluded_file(item.name, api_cfg)
        ],
        key=lambda item: item.name.lower(),
    )


def _iter_subdirs(src: Path, api_cfg: ApiConfig) -> list[Path]:
    return sorted(
        [
            item
            for item in src.iterdir()
            if item.is_dir() and not _is_excluded_dir(item.name, api_cfg)
        ],
        key=lambda item: item.name.lower(),
    )


def _module_path(py_file: Path, project_root: Path) -> str:
    rel = py_file.relative_to(project_root).with_suffix("")
    return ".".join(rel.parts)


def _relative_to_docs_src(path: Path, cfg: DocToolsConfig) -> str:
    return path.relative_to(cfg.docs_src_dir).as_posix()


def _is_excluded_dir(name: str, api_cfg: ApiConfig) -> bool:
    return name in api_cfg.exclude_dirs


def _is_excluded_file(name: str, api_cfg: ApiConfig) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in api_cfg.exclude_files)


def _folder_line(*, indent: int, label: str, use_emojis: bool) -> str:
    prefix = "  " * indent
    icon = "📂 " if use_emojis else ""
    return f"{prefix}- {icon}{label}:"


def _nav_line(
    *,
    indent: int,
    label: str,
    rel_path: str,
    use_emojis: bool,
    kind: str,
) -> str:
    prefix = "  " * indent
    icon = ""

    if use_emojis:
        icon = {
            "overview": "🗺️ ",
            "intro": "📖 ",
            "file": "📄 ",
        }.get(kind, "")

    return f"{prefix}- {icon}{label}: {rel_path}"


def _indent_line(line: str, indent: int) -> str:
    return f"{'  ' * indent}{line}" if line.strip() else ""
