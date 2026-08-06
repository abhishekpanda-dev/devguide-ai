import os
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import RepositoryLimitExceededError, RepositoryWorkspaceError

EXCLUDED_DIRECTORIES = frozenset(
    {".git", "node_modules", ".venv", "venv", "dist", "build", "coverage", "__pycache__"}
)


@dataclass(frozen=True, slots=True)
class RepositoryScanResult:
    file_count: int
    size_bytes: int
    skipped_directory_count: int
    limitations: tuple[str, ...]


class RepositoryScanner:
    def __init__(
        self,
        *,
        maximum_file_count: int,
        maximum_repository_size_bytes: int,
        maximum_individual_file_size_bytes: int,
    ) -> None:
        self._maximum_file_count = maximum_file_count
        self._maximum_repository_size_bytes = maximum_repository_size_bytes
        self._maximum_individual_file_size_bytes = maximum_individual_file_size_bytes

    def scan(self, repository_path: Path) -> RepositoryScanResult:
        file_count = 0
        size_bytes = 0
        skipped_directory_count = 0
        skipped_symlinks = 0
        pending = [repository_path]

        try:
            while pending:
                directory = pending.pop()
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if entry.is_symlink():
                            skipped_symlinks += 1
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.casefold() in EXCLUDED_DIRECTORIES:
                                skipped_directory_count += 1
                            else:
                                pending.append(Path(entry.path))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue

                        file_size = entry.stat(follow_symlinks=False).st_size
                        if file_size > self._maximum_individual_file_size_bytes:
                            raise RepositoryLimitExceededError(
                                "A repository file exceeds the configured size limit."
                            )
                        file_count += 1
                        if file_count > self._maximum_file_count:
                            raise RepositoryLimitExceededError(
                                "The repository exceeds the configured file-count limit."
                            )
                        size_bytes += file_size
                        if size_bytes > self._maximum_repository_size_bytes:
                            raise RepositoryLimitExceededError(
                                "The repository exceeds the configured total-size limit."
                            )
        except RepositoryLimitExceededError:
            raise
        except OSError as exc:
            raise RepositoryWorkspaceError from exc

        limitations = (
            ["Symbolic links were skipped during repository limit scanning."]
            if skipped_symlinks
            else []
        )
        return RepositoryScanResult(
            file_count=file_count,
            size_bytes=size_bytes,
            skipped_directory_count=skipped_directory_count,
            limitations=tuple(limitations),
        )
