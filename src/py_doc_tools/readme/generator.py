# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""README documentation mirroring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


def generate_readme_docs(cfg: DocToolsConfig, console: Console) -> int:
    """Copy README content into the documentation tree."""
    if cfg.readme is None:
        msg = "readme"
        raise MissingConfigSectionError(msg)

    readme_cfg = cfg.readme

    if not readme_cfg.source_file.exists():
        console.warn(f"README source file not found: {readme_cfg.source_file}")
        return 0

    readme_cfg.output_file.parent.mkdir(parents=True, exist_ok=True)

    source = readme_cfg.source_file.read_text(encoding="utf-8")
    content = source

    if readme_cfg.include_toc_note:
        content = "\n".join(
            [
                f"# {readme_cfg.title}",
                "",
                "This page is generated from the project README.",
                "",
                "---",
                "",
                source,
                "",
            ],
        )

    _ = readme_cfg.output_file.write_text(content, encoding="utf-8")
    console.ok(f"README documentation generated: {readme_cfg.output_file}")
    return 0
