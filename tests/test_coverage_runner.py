"""Tests for coverage runner."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import py_doc_tools.coverage.runner as coverage_runner
from py_doc_tools.config.model import CoverageConfig, DocToolsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from pathlib import Path

SUCCESS_CODE = 0
FAILURE_CODE = 1


def _base_config(tmp_path: Path) -> DocToolsConfig:
    return DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_coverage=True,
        coverage=CoverageConfig(
            package="demo",
            output_dir=tmp_path / "docs" / "coverage",
            branch=True,
            quiet=True,
        ),
    )


def test_run_coverage_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Coverage runner returns zero when pytest succeeds."""
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

    monkeypatch.setattr(coverage_runner, "run_command", fake_run_command)

    cfg = _base_config(tmp_path)
    code = coverage_runner.run_coverage(cfg, Console())

    assert code == SUCCESS_CODE
    assert calls
    assert "--cov=demo" in calls[0]
    assert "--cov-branch" in calls[0]
    assert "--no-header" in calls[0]
    assert "-q" in calls[0]


def test_run_coverage_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Coverage runner returns pytest exit code when pytest fails."""

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
            returncode=FAILURE_CODE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(coverage_runner, "run_command", fake_run_command)

    cfg = _base_config(tmp_path)
    code = coverage_runner.run_coverage(cfg, Console())

    assert code == FAILURE_CODE


def test_run_coverage_uses_first_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Coverage runner falls back to the first configured package."""
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

    monkeypatch.setattr(coverage_runner, "run_command", fake_run_command)

    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["fallback_pkg"],
        coverage=CoverageConfig(package=None),
    )

    code = coverage_runner.run_coverage(cfg, Console())

    assert code == SUCCESS_CODE
    assert "--cov=fallback_pkg" in calls[0]


def test_run_coverage_without_branch_or_quiet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Coverage runner can skip branch and quiet flags."""
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

    monkeypatch.setattr(coverage_runner, "run_command", fake_run_command)

    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        coverage=CoverageConfig(
            package="demo",
            branch=False,
            quiet=False,
        ),
    )

    code = coverage_runner.run_coverage(cfg, Console())

    assert code == SUCCESS_CODE
    assert "--cov-branch" not in calls[0]
    assert "--no-header" not in calls[0]
    assert "-q" not in calls[0]


def test_run_coverage_missing_config(tmp_path: Path) -> None:
    """Missing coverage config raises a dedicated error."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        coverage=None,
    )

    with pytest.raises(MissingConfigSectionError, match="coverage"):
        _ = coverage_runner.run_coverage(cfg, Console())


def test_run_coverage_missing_package(tmp_path: Path) -> None:
    """Missing coverage package raises a dedicated error."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=[],
        coverage=CoverageConfig(package=None),
    )

    with pytest.raises(MissingConfigSectionError, match=r"coverage\.package"):
        _ = coverage_runner.run_coverage(cfg, Console())
