from collections import Counter

from app.parser.types import RepositoryStatistics, SourceChunk, SourceFile


def build_statistics(
    *,
    files: tuple[SourceFile, ...],
    chunks: tuple[SourceChunk, ...],
    discovered_files: int,
    skipped_directories: int,
    parser_version: str,
    limitations: tuple[str, ...],
) -> RepositoryStatistics:
    file_counts = Counter(item.metadata.language for item in files)
    line_counts: Counter[str] = Counter()
    for item in files:
        line_counts[item.metadata.language] += item.metadata.line_count
    sizes = sorted(
        ((item.metadata.size_bytes, item.metadata.path) for item in files),
        key=lambda value: (value[0], value[1]),
    )
    return RepositoryStatistics(
        total_files_discovered=discovered_files,
        accepted_source_files=len(files),
        skipped_files=discovered_files - len(files),
        skipped_directories=skipped_directories,
        total_accepted_bytes=sum(item.metadata.size_bytes for item in files),
        total_accepted_lines=sum(item.metadata.line_count for item in files),
        file_count_by_language=dict(sorted(file_counts.items())),
        line_count_by_language=dict(sorted(line_counts.items())),
        documentation_file_count=sum(item.metadata.is_documentation for item in files),
        configuration_file_count=sum(item.metadata.is_configuration for item in files),
        test_file_count=sum(item.metadata.is_test for item in files),
        largest_accepted_file=sizes[-1][1] if sizes else None,
        smallest_accepted_file=sizes[0][1] if sizes else None,
        total_chunks=len(chunks),
        parser_version=parser_version,
        limitations=limitations,
    )
