"""Additional branch tests for CLI dispatch."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from py_doc_tools import cli
from py_doc_tools.config.model import ApiConfig, DocToolsConfig
from py_doc_tools.core.console import Console

if TYPE_CHECKING:
    from pathlib import Path

MKDOCS_BUILD_EXIT_CODE = 7
MKDOCS_SERVE_EXIT_CODE = 3
SUCCESS_CODE = 0


def _base_config(tmp_path: Path) -> DocToolsConfig:
    return DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        api=ApiConfig(output_dir=tmp_path / "docs" / "api"),
    )


def test_cli_dispatch_generate_all(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches generate --all."""
    calls: list[str] = []

    def fake_generate_all(cfg: DocToolsConfig, console: Console) -> None:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append("all")

    monkeypatch.setattr(cli, "generate_all", fake_generate_all)

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="generate",
        generate_all=True,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command=None,
        strict=False,
        clean_command=None,
    )

    _ = cli.dispatch(args, _base_config(tmp_path), Console())

    assert calls == ["all"]


def test_cli_dispatch_generate_coverage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches generate --coverage."""
    calls: list[str] = []

    def fake_generate_coverage(cfg: DocToolsConfig, console: Console) -> None:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append("coverage")

    monkeypatch.setattr(cli, "generate_coverage", fake_generate_coverage)

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="generate",
        generate_all=False,
        generate_api=False,
        generate_coverage=True,
        mkdocs_command=None,
        strict=False,
        clean_command=None,
    )

    _ = cli.dispatch(args, _base_config(tmp_path), Console())

    assert calls == ["coverage"]


def test_cli_dispatch_generate_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches generate --api."""
    calls: list[str] = []

    def fake_generate_api(cfg: DocToolsConfig, console: Console) -> None:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        calls.append("api")

    monkeypatch.setattr(cli, "generate_api", fake_generate_api)

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="generate",
        generate_all=False,
        generate_api=True,
        generate_coverage=False,
        mkdocs_command=None,
        strict=False,
        clean_command=None,
    )

    _ = cli.dispatch(args, _base_config(tmp_path), Console())

    assert calls == ["api"]


def test_cli_dispatch_generate_without_target(tmp_path: Path) -> None:
    """CLI exits when generate has no selected target."""
    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="generate",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command=None,
        strict=False,
        clean_command=None,
    )

    with pytest.raises(SystemExit, match="No generation target selected"):
        _ = cli.dispatch(args, _base_config(tmp_path), Console())


def test_cli_dispatch_mkdocs_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches mkdocs build."""

    def fake_run_mkdocs_build(
        cfg: DocToolsConfig,
        console: Console,
        *,
        strict: bool = False,
    ) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        assert strict is True

        return MKDOCS_BUILD_EXIT_CODE

    monkeypatch.setattr(cli, "run_mkdocs_build", fake_run_mkdocs_build)

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="mkdocs",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command="build",
        strict=True,
        clean_command=None,
    )

    with pytest.raises(SystemExit) as exc_info:
        _ = cli.dispatch(args, _base_config(tmp_path), Console())

    assert exc_info.value.code == MKDOCS_BUILD_EXIT_CODE


def test_cli_dispatch_mkdocs_serve(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches mkdocs serve."""

    def fake_run_mkdocs_serve(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)

        return MKDOCS_SERVE_EXIT_CODE

    monkeypatch.setattr(cli, "run_mkdocs_serve", fake_run_mkdocs_serve)

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="mkdocs",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command="serve",
        strict=False,
        clean_command=None,
    )

    with pytest.raises(SystemExit) as exc_info:
        _ = cli.dispatch(args, _base_config(tmp_path), Console())

    assert exc_info.value.code == MKDOCS_SERVE_EXIT_CODE


def test_cli_dispatch_unknown_mkdocs_command(tmp_path: Path) -> None:
    """CLI exits on unknown mkdocs command."""
    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="mkdocs",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command="unknown",
        strict=False,
        clean_command=None,
    )

    with pytest.raises(SystemExit, match="Unknown mkdocs command"):
        _ = cli.dispatch(args, _base_config(tmp_path), Console())


def test_cli_dispatch_clean_api(tmp_path: Path) -> None:
    """CLI dispatches clean api."""
    cfg = _base_config(tmp_path)

    if cfg.api is None:
        pytest.fail("API config should exist.")

    cfg.api.output_dir.mkdir(parents=True)

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="clean",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command=None,
        strict=False,
        clean_command="api",
    )

    _ = cli.dispatch(args, cfg, Console())

    assert not cfg.api.output_dir.exists()


def test_cli_unknown_command(tmp_path: Path) -> None:
    """Unknown top-level command exits."""
    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="unknown",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command=None,
        strict=False,
        clean_command=None,
    )

    with pytest.raises(SystemExit, match="Unknown command"):
        _ = cli.dispatch(args, _base_config(tmp_path), Console())


def test_cli_clean_api_missing_config(tmp_path: Path) -> None:
    """Cleaning API without API config exits."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        api=None,
    )

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="clean",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command=None,
        strict=False,
        clean_command="api",
    )

    with pytest.raises(SystemExit, match="API configuration is missing"):
        _ = cli.dispatch(args, cfg, Console())


def test_cli_unknown_clean_command(tmp_path: Path) -> None:
    """CLI exits on unknown clean command."""
    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="clean",
        generate_all=False,
        generate_api=False,
        generate_coverage=False,
        mkdocs_command=None,
        strict=False,
        clean_command="unknown",
    )

    with pytest.raises(SystemExit, match="Unknown clean command"):
        _ = cli.dispatch(args, _base_config(tmp_path), Console())

def test_cli_dispatch_tags_clean_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches tags clean in dry-run mode by default."""
    calls: list[bool | None] = []

    def fake_clean_generated_source_tags(
        cfg: DocToolsConfig,
        console: Console,
        *,
        dry_run: bool | None = None,
    ) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append(dry_run)
        return SUCCESS_CODE

    monkeypatch.setattr(
        cli,
        "clean_generated_source_tags",
        fake_clean_generated_source_tags,
    )

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="tags",
        tags_command="clean",
        write=False,
        dry_run=False,
    )

    code = cli.dispatch(args, _base_config(tmp_path), Console())

    assert code == SUCCESS_CODE
    assert calls == [True]


def test_cli_dispatch_tags_clean_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches tags clean in write mode."""
    calls: list[bool | None] = []

    def fake_clean_generated_source_tags(
        cfg: DocToolsConfig,
        console: Console,
        *,
        dry_run: bool | None = None,
    ) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append(dry_run)
        return SUCCESS_CODE

    monkeypatch.setattr(
        cli,
        "clean_generated_source_tags",
        fake_clean_generated_source_tags,
    )

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="tags",
        tags_command="clean",
        write=True,
        dry_run=False,
    )

    code = cli.dispatch(args, _base_config(tmp_path), Console())

    assert code == SUCCESS_CODE
    assert calls == [False]


def test_cli_dispatch_tags_inject(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI dispatches tags inject."""
    calls: list[str] = []

    def fake_inject_source_tags(cfg: DocToolsConfig, console: Console) -> int:
        assert cfg.project_root == tmp_path
        assert isinstance(console, Console)
        calls.append("inject")
        return SUCCESS_CODE

    monkeypatch.setattr(cli, "inject_source_tags", fake_inject_source_tags)

    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="tags",
        tags_command="inject",
    )

    code = cli.dispatch(args, _base_config(tmp_path), Console())

    assert code == SUCCESS_CODE
    assert calls == ["inject"]


def test_cli_dispatch_unknown_tags_command(tmp_path: Path) -> None:
    """CLI exits on unknown tags command."""
    args = cli.CliArgs(
        root=tmp_path,
        verbose=False,
        command="tags",
        tags_command="unknown",
    )

    with pytest.raises(SystemExit, match="Unknown tags command"):
        _ = cli.dispatch(args, _base_config(tmp_path), Console())
