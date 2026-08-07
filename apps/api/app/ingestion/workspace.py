import os
import shutil
import stat
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType

from app.core.exceptions import RepositoryWorkspaceError

CLEANUP_ATTEMPTS = 3
CLEANUP_RETRY_DELAY_SECONDS = 0.05


class RepositoryWorkspace:
    def __init__(self, root: Path) -> None:
        self._configured_root = root
        self._root: Path | None = None
        self._workspace_path: Path | None = None

    @property
    def path(self) -> Path:
        if self._workspace_path is None:
            raise RepositoryWorkspaceError
        return self._workspace_path

    @property
    def repository_path(self) -> Path:
        return self.path / "repository"

    @property
    def metadata_path(self) -> Path:
        return self.path / "metadata"

    def __enter__(self) -> "RepositoryWorkspace":
        try:
            self._configured_root.mkdir(parents=True, exist_ok=True)
            if self._configured_root.is_symlink():
                raise RepositoryWorkspaceError
            self._root = self._configured_root.resolve(strict=True)
            created = Path(tempfile.mkdtemp(prefix="ingestion-", dir=self._root))
            self._workspace_path = created.resolve(strict=True)
            self.validate_path(self._workspace_path)
            self.repository_path.mkdir()
            self.metadata_path.mkdir()
            return self
        except RepositoryWorkspaceError:
            self._cleanup_created_path()
            raise
        except OSError as exc:
            self._cleanup_created_path()
            raise RepositoryWorkspaceError from exc

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.cleanup()

    def validate_path(self, path: Path) -> Path:
        if self._root is None:
            raise RepositoryWorkspaceError
        try:
            resolved = path.resolve(strict=False)
        except OSError as exc:
            raise RepositoryWorkspaceError from exc
        if not resolved.is_relative_to(self._root):
            raise RepositoryWorkspaceError
        return resolved

    def cleanup(self) -> None:
        path = self._workspace_path
        if path is None or not path.exists():
            return
        if path.is_symlink():
            raise RepositoryWorkspaceError
        resolved = self.validate_path(path)
        if resolved == self._root:
            raise RepositoryWorkspaceError
        for attempt in range(CLEANUP_ATTEMPTS):
            try:
                shutil.rmtree(resolved, onerror=self._remove_readonly)
                return
            except OSError as exc:
                if attempt == CLEANUP_ATTEMPTS - 1:
                    raise RepositoryWorkspaceError from exc
                time.sleep(CLEANUP_RETRY_DELAY_SECONDS)

    def _remove_readonly(
        self,
        function: Callable[[str], object],
        path: str,
        _exc_info: tuple[type[BaseException], BaseException, TracebackType | None],
    ) -> None:
        candidate = Path(path)
        if candidate.is_symlink():
            raise RepositoryWorkspaceError
        self.validate_path(candidate)
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        function(path)

    def _cleanup_created_path(self) -> None:
        if self._workspace_path is None:
            return
        try:
            self.cleanup()
        except RepositoryWorkspaceError:
            pass
