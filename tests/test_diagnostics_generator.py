"""Tests for diagnostics documentation generation."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, cast

import pytest

import py_doc_tools.diagnostics.generator as diagnostics_generator
from py_doc_tools.config.model import DiagnosticsConfig, DocToolsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

SUCCESS_CODE = 0
RUFF_FAILURE_CODE = 2
MKDOCS_FAILURE_CODE = 1
EXPECTED_CALL_COUNT = 2


def _make_config(**kwargs: object) -> DocToolsConfig:
    config_cls = cast("Callable[..., DocToolsConfig]", DocToolsConfig)
    return config_cls(**kwargs)


def _make_diagnostics_config(**kwargs: object) -> DiagnosticsConfig:
    config_cls = cast("Callable[..., DiagnosticsConfig]", DiagnosticsConfig)
    return config_cls(**kwargs)


def _base_config(
    tmp_path: Path,
    diagnostics: DiagnosticsConfig | None,
) -> DocToolsConfig:
    return _make_config(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_diagnostics=diagnostics is not None,
        diagnostics=diagnostics,
    )


def _diagnostics_config(tmp_path: Path) -> DiagnosticsConfig:
    return _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=True,
        mkdocs_strict=True,
    )


def _assert_common_subprocess_kwargs(
    kwargs: Mapping[str, object],
    *,
    expected_cwd: Path,
) -> None:
    assert kwargs["cwd"] == expected_cwd
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"

    env = cast("dict[str, str]", kwargs["env"])
    assert env["PYTHONIOENCODING"] == "utf-8"
    assert env["PYTHONUTF8"] == "1"


def _assert_ruff_command(command: list[str]) -> None:
    assert command[:5] == [
        sys.executable,
        "-m",
        "ruff",
        "check",
        ".",
    ]
    assert "--exclude" in command
    assert ".pixi" in command
    assert "docs/build" in command


def test_generate_diagnostics_docs_runs_ruff_and_mkdocs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator captures Ruff and MkDocs outputs."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="ok stdout",
            stderr="ok stderr",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _diagnostics_config(tmp_path)
    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == SUCCESS_CODE
    assert len(calls) == EXPECTED_CALL_COUNT
    _assert_ruff_command(calls[0])
    assert "--strict" in calls[1]

    assert "Ruff diagnostics" in diagnostics.ruff_output_file.read_text(
        encoding="utf-8",
    )
    assert "MkDocs diagnostics" in diagnostics.mkdocs_output_file.read_text(
        encoding="utf-8",
    )


def test_generate_diagnostics_docs_returns_highest_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator returns the highest command exit code."""
    return_codes = [RUFF_FAILURE_CODE, MKDOCS_FAILURE_CODE]

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=return_codes.pop(0),
            stdout="",
            stderr="error",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    cfg = _base_config(tmp_path, _diagnostics_config(tmp_path))

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console())
        == RUFF_FAILURE_CODE
    )


def test_generate_diagnostics_docs_can_disable_commands(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator respects enable flags."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=False,
        enable_mkdocs=False,
        mkdocs_strict=False,
    )
    cfg = _base_config(tmp_path, diagnostics)

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console()) == SUCCESS_CODE
    )
    assert calls == []


def test_generate_diagnostics_docs_missing_config(tmp_path: Path) -> None:
    """Missing diagnostics config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="diagnostics"):
        _ = diagnostics_generator.generate_diagnostics_docs(cfg, Console())


def test_generate_diagnostics_docs_only_ruff_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator can run only Ruff."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="ruff only",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=False,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console()) == SUCCESS_CODE
    )
    assert len(calls) == 1
    _assert_ruff_command(calls[0])
    assert diagnostics.ruff_output_file.exists()
    assert not diagnostics.mkdocs_output_file.exists()


def test_generate_diagnostics_docs_only_mkdocs_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator can run only MkDocs."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="mkdocs only",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=False,
        enable_mkdocs=True,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console()) == SUCCESS_CODE
    )
    assert len(calls) == 1
    assert "mkdocs" in calls[0]
    assert not diagnostics.ruff_output_file.exists()
    assert diagnostics.mkdocs_output_file.exists()


def test_generate_diagnostics_docs_handles_missing_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator reports missing commands without crashing."""

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=False,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == 1
    assert diagnostics.ruff_output_file.exists()
    assert "could not be executed" in diagnostics.ruff_output_file.read_text(
        encoding="utf-8",
    )


def test_generate_diagnostics_docs_handles_missing_mkdocs_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator reports missing MkDocs command without crashing."""

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=False,
        enable_mkdocs=True,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == 1
    assert diagnostics.mkdocs_output_file.exists()
    assert "could not be executed" in diagnostics.mkdocs_output_file.read_text(
        encoding="utf-8",
    )
