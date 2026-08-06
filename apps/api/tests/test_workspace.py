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
