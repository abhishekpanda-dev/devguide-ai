import hashlib
from pathlib import PurePosixPath, PureWindowsPath

from app.repositories.parsed import SearchCandidate


class CitationValidator:
    """Fail-closed validation for persisted citation provenance."""

    @staticmethod
    def validate(candidate: SearchCandidate) -> tuple[str, ...]:
        failures: list[str] = []
        path = PurePosixPath(candidate.path)
        if (
            not candidate.path
            or "\\" in candidate.path
            or path.is_absolute()
            or PureWindowsPath(candidate.path).is_absolute()
            or ".." in path.parts
        ):
            failures.append("invalid_repository_relative_path")
        if not (1 <= candidate.start_line <= candidate.end_line <= candidate.file_line_count):
            failures.append("invalid_line_range")
        actual_hash = hashlib.sha256(candidate.content.encode()).hexdigest()
        if actual_hash != candidate.content_hash:
            failures.append("content_hash_mismatch")
        if not candidate.commit_sha.strip():
            failures.append("missing_commit_sha")
        return tuple(failures)
