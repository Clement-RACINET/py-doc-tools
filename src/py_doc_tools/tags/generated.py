"""Generated source tag formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from py_doc_tools.issues.model import DiagnosticIssue


def render_generated_tag(
    issue: DiagnosticIssue,
    *,
    prefix: str = "py-doc-tools",
) -> str:
    """Render an auto-generated source tag for one diagnostic issue."""
    marker = _marker_for_issue(issue)
    source = issue.source
    code = issue.code or "UNKNOWN"
    message = issue.message.strip().replace("\n", " ")

    return f"# {marker}[{prefix}:{source}:{code}]: {message}"


def _marker_for_issue(issue: DiagnosticIssue) -> str:
    if issue.severity == "todo":
        return "TODO"

    return "FIXME"
