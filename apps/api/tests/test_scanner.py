from pathlib import Path

import pytest

from app.core.exceptions import RepositoryLimitExceededError
from app.ingestion.scanner import RepositoryScanner


def scanner(
    *, files: int = 10, repository_bytes: int = 100, file_bytes: int = 50
) -> RepositoryScanner:
    return RepositoryScanner(
        maximum_file_count=files,
        maximum_repository_size_bytes=repository_bytes,
        maximum_individual_file_size_bytes=file_bytes,
    )


def test_git_and_other_excluded_directories_are_not_enumerated(tmp_path: Path) -> None:
    (tmp_path / "source.py").write_bytes(b"source")
    for name in (
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "coverage",
        "__pycache__",
    ):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "ignored.bin").write_bytes(b"x" * 100)

    result = scanner(repository_bytes=10).scan(tmp_path)

    assert result.file_count == 1
    assert result.size_bytes == 6
    assert result.skipped_directory_count == 8


def test_file_count_limit_is_enforced(tmp_path: Path) -> None:
    (tmp_path / "one").write_bytes(b"1")
    (tmp_path / "two").write_bytes(b"2")
    with pytest.raises(RepositoryLimitExceededError, match="file-count"):
        scanner(files=1).scan(tmp_path)


def test_repository_size_limit_is_enforced(tmp_path: Path) -> None:
    (tmp_path / "one").write_bytes(b"123456")
    (tmp_path / "two").write_bytes(b"123456")
    with pytest.raises(RepositoryLimitExceededError, match="total-size"):
        scanner(repository_bytes=10, file_bytes=10).scan(tmp_path)


def test_individual_file_size_limit_is_enforced(tmp_path: Path) -> None:
    (tmp_path / "large").write_bytes(b"123456")
    with pytest.raises(RepositoryLimitExceededError, match="file exceeds"):
        scanner(file_bytes=5).scan(tmp_path)
