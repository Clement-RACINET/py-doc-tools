"""MkDocs navigation update helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.markers import replace_between_markers

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig


def update_api_nav(cfg: DocToolsConfig, nav_block: str) -> None:
    """Update the API navigation block in ``mkdocs.yml``.

    Args:
        cfg: Root tool configuration.
        nav_block: Generated navigation block.
    """
    if cfg.api is None:
        msg = "api"
        raise MissingConfigSectionError(msg)

    replace_between_markers(
        file_path=cfg.mkdocs_config,
        start_marker=cfg.api.nav_start_marker,
        end_marker=cfg.api.nav_end_marker,
        new_block=nav_block,
        preserve_marker_indent=True,
    )
