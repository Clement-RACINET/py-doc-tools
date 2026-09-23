# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for MkDocs runners."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import py_doc_tools.mkdocs.runner as mkdocs_runner
from py_doc_tools.config.model import DocToolsConfig
from py_doc_tools.core.console import Console

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

SUCCESS_CODE = 0
BUILD_FAILURE_CODE = 2


def _base_config(tmp_path: Path) -> DocToolsConfig:
    return DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
    )


def test_run_mkdocs_build_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """MkDocs build returns zero on success."""
    calls: list[list[str]] = []

    def fake_run_command(
        cmd: list[str],
        *,
        cwd: Path,
        check: bool = False,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert check is False
        assert capture_output is False

        calls.append(cmd)

        return subprocess.CompletedProcess[str](
            args=cmd,
            returncode=SUCCESS_CODE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(mkdocs_runner, "run_command", fake_run_command)

    code = mkdocs_runner.run_mkdocs_build(
        _base_config(tmp_path),
        Console(),
        strict=True,
    )

    assert code == SUCCESS_CODE
    assert "--strict" in calls[0]


def test_run_mkdocs_build_success_without_strict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """MkDocs build can run without strict mode."""
    calls: list[list[str]] = []

    def fake_run_command(
        cmd: list[str],
        *,
        cwd: Path,
        check: bool = False,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert check is False
        assert capture_output is False

        calls.append(cmd)

        return subprocess.CompletedProcess[str](
            args=cmd,
            returncode=SUCCESS_CODE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(mkdocs_runner, "run_command", fake_run_command)

    code = mkdocs_runner.run_mkdocs_build(_base_config(tmp_path), Console())

    assert code == SUCCESS_CODE
    assert "--strict" not in calls[0]


def test_run_mkdocs_build_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """MkDocs build returns the failing exit code."""

    def fake_run_command(
        cmd: list[str],
        *,
        cwd: Path,
        check: bool = False,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert check is False
        assert capture_output is False

        return subprocess.CompletedProcess[str](
            args=cmd,
            returncode=BUILD_FAILURE_CODE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(mkdocs_runner, "run_command", fake_run_command)

    code = mkdocs_runner.run_mkdocs_build(_base_config(tmp_path), Console())

    assert code == BUILD_FAILURE_CODE


def test_run_mkdocs_serve(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """MkDocs serve returns the subprocess exit code."""
    calls: list[list[str]] = []

    def fake_run_command(
        cmd: list[str],
        *,
        cwd: Path,
        check: bool = False,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert check is False
        assert capture_output is False

        calls.append(cmd)

        return subprocess.CompletedProcess[str](
            args=cmd,
            returncode=SUCCESS_CODE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(mkdocs_runner, "run_command", fake_run_command)

    code = mkdocs_runner.run_mkdocs_serve(_base_config(tmp_path), Console())

    assert code == SUCCESS_CODE
    assert calls[0][-1] == "serve"
