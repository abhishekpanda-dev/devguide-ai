import os
from pathlib import Path

from app.parser.chunking import TextChunker
from app.parser.filters import appears_binary, is_explicitly_rejected, is_ignored_directory
from app.parser.languages import detect_language
from app.parser.metadata import build_metadata
from app.parser.statistics import build_statistics
from app.parser.types import RepositoryParseResult, SourceChunk, SourceFile


class RepositoryParser:
    def __init__(
        self,
        *,
        maximum_file_size_bytes: int = 5 * 1024 * 1024,
        maximum_lines_per_chunk: int = 200,
        overlap_lines: int = 20,
        parser_version: str = "1",
    ) -> None:
        if maximum_file_size_bytes < 1:
            raise ValueError("maximum_file_size_bytes must be at least 1")
        self._maximum_file_size_bytes = maximum_file_size_bytes
        self._chunker = TextChunker(
            maximum_lines=maximum_lines_per_chunk,
            overlap_lines=overlap_lines,
            parser_version=parser_version,
        )
        self._parser_version = parser_version

    def parse(self, repository_root: Path) -> RepositoryParseResult:
        if repository_root.is_symlink():
            raise ValueError("repository_root must not be a symbolic link")
        root = repository_root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("repository_root must be a directory")

        discovered_files = 0
        skipped_directories = 0
        limitations: list[str] = []
        files: list[SourceFile] = []
        pending = [root]

        while pending:
            directory = pending.pop()
            try:
                with os.scandir(directory) as iterator:
                    entries = sorted(iterator, key=lambda item: item.name.casefold())
            except OSError:
                limitations.append(self._limitation(root, directory, "directory could not be read"))
                continue
            for entry in entries:
                path = Path(entry.path)
                try:
                    if entry.is_symlink():
                        if entry.is_dir(follow_symlinks=False):
                            skipped_directories += 1
                        else:
                            discovered_files += 1
                        limitations.append(
                            self._limitation(root, path, "symbolic link was skipped")
                        )
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if is_ignored_directory(entry.name):
                            skipped_directories += 1
                        else:
                            pending.append(path)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    discovered_files += 1
                    parsed, limitation = self._parse_file(root, path)
                    if parsed is not None:
                        files.append(parsed)
                    if limitation is not None:
                        limitations.append(self._limitation(root, path, limitation))
                except OSError:
                    limitations.append(self._limitation(root, path, "file could not be inspected"))

        ordered_files = tuple(sorted(files, key=lambda item: item.metadata.path))
        chunks: list[SourceChunk] = []
        for source_file in ordered_files:
            chunks.extend(self._chunker.chunk(source_file.metadata, source_file.content))
        ordered_chunks = tuple(sorted(chunks, key=lambda item: (item.path, item.start_line)))
        ordered_limitations = tuple(sorted(set(limitations)))
        statistics = build_statistics(
            files=ordered_files,
            chunks=ordered_chunks,
            discovered_files=discovered_files,
            skipped_directories=skipped_directories,
            parser_version=self._parser_version,
            limitations=ordered_limitations,
        )
        return RepositoryParseResult(ordered_files, ordered_chunks, statistics)

    def _parse_file(self, root: Path, path: Path) -> tuple[SourceFile | None, str | None]:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved != path.absolute():
            return None, "path escaped the repository root"
        if is_explicitly_rejected(path) or detect_language(path) is None:
            return None, None
        if path.stat(follow_symlinks=False).st_size > self._maximum_file_size_bytes:
            return None, None
        try:
            data = path.read_bytes()
        except OSError:
            return None, "file could not be read"
        if len(data) > self._maximum_file_size_bytes or appears_binary(data):
            return None, None
        encoding = "utf-8-sig" if data.startswith(b"\xef\xbb\xbf") else "utf-8"
        try:
            content = data.decode(encoding)
        except UnicodeDecodeError:
            return None, None
        relative_path = path.relative_to(root).as_posix()
        language = detect_language(path)
        if language is None:
            return None, None
        metadata = build_metadata(
            relative_path=relative_path,
            language=language,
            data=data,
            content=content,
            encoding=encoding,
        )
        return SourceFile(metadata=metadata, content=content), None

    @staticmethod
    def _limitation(root: Path, path: Path, reason: str) -> str:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = "<outside-repository>"
        return f"{relative}: {reason}."
