from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceFileMetadata:
    path: str
    file_name: str
    extension: str
    language: str
    size_bytes: int
    line_count: int
    content_hash: str
    is_test: bool
    is_documentation: bool
    is_configuration: bool
    is_generated: bool
    encoding: str | None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceFile:
    metadata: SourceFileMetadata
    content: str


@dataclass(frozen=True, slots=True)
class SourceChunk:
    chunk_id: str
    path: str
    language: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True, slots=True)
class RepositoryStatistics:
    total_files_discovered: int
    accepted_source_files: int
    skipped_files: int
    skipped_directories: int
    total_accepted_bytes: int
    total_accepted_lines: int
    file_count_by_language: dict[str, int]
    line_count_by_language: dict[str, int]
    documentation_file_count: int
    configuration_file_count: int
    test_file_count: int
    largest_accepted_file: str | None
    smallest_accepted_file: str | None
    total_chunks: int
    parser_version: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RepositoryParseResult:
    files: tuple[SourceFile, ...]
    chunks: tuple[SourceChunk, ...]
    statistics: RepositoryStatistics
