import os
import shutil
import stat
from pathlib import Path

import pytest

from app.core.exceptions import RepositoryWorkspaceError
from app.ingestion.workspace import RepositoryWorkspace


def test_workspace_is_created_under_configured_root_and_cleaned(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    with RepositoryWorkspace(root) as workspace:
        created_path = workspace.path
        assert created_path.is_relative_to(root.resolve())
        assert workspace.repository_path.is_dir()
        assert workspace.metadata_path.is_dir()
    assert not created_path.exists()


def test_workspace_is_cleaned_when_body_raises(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    created_path: Path | None = None
    with pytest.raises(RuntimeError):
        with RepositoryWorkspace(root) as workspace:
            created_path = workspace.path
            raise RuntimeError("forced failure")
    assert created_path is not None and not created_path.exists()


def test_workspace_validation_prevents_escape_and_outside_deletion(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with RepositoryWorkspace(root) as workspace:
        with pytest.raises(RepositoryWorkspaceError):
            workspace.validate_path(outside)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_workspace_cleanup_retries_transient_permission_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspaces"
    workspace = RepositoryWorkspace(root)
    workspace.__enter__()
    created_path = workspace.path
    original_rmtree = shutil.rmtree
    attempts = 0

    def transient_rmtree(path: Path, **_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError
        original_rmtree(path)

    monkeypatch.setattr("app.ingestion.workspace.shutil.rmtree", transient_rmtree)
    monkeypatch.setattr("app.ingestion.workspace.time.sleep", lambda _delay: None)

    workspace.cleanup()

    assert attempts == 2
    assert not created_path.exists()


def test_workspace_cleanup_removes_readonly_file(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    with RepositoryWorkspace(root) as workspace:
        created_path = workspace.path
        readonly = workspace.repository_path / "readonly.txt"
        readonly.write_text("content", encoding="utf-8")
        os.chmod(readonly, stat.S_IREAD)

    assert not created_path.exists()


def test_workspace_cleanup_path_escape_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    workspace = RepositoryWorkspace(root)
    workspace.__enter__()
    created_path = workspace.path
    workspace._workspace_path = outside

    with pytest.raises(RepositoryWorkspaceError):
        workspace.cleanup()

    assert marker.read_text(encoding="utf-8") == "keep"
    shutil.rmtree(created_path)
