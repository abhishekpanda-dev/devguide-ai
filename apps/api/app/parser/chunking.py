import hashlib

from app.parser.types import SourceChunk, SourceFileMetadata


class TextChunker:
    def __init__(
        self, *, maximum_lines: int = 200, overlap_lines: int = 20, parser_version: str = "1"
    ) -> None:
        if maximum_lines < 1:
            raise ValueError("maximum_lines must be at least 1")
        if overlap_lines < 0 or overlap_lines >= maximum_lines:
            raise ValueError("overlap_lines must be non-negative and smaller than maximum_lines")
        if not parser_version.strip():
            raise ValueError("parser_version must not be empty")
        self.maximum_lines = maximum_lines
        self.overlap_lines = overlap_lines
        self.parser_version = parser_version

    def chunk(self, metadata: SourceFileMetadata, content: str) -> tuple[SourceChunk, ...]:
        lines = content.splitlines()
        if not lines:
            return ()
        chunks: list[SourceChunk] = []
        step = self.maximum_lines - self.overlap_lines
        for offset in range(0, len(lines), step):
            selected = lines[offset : offset + self.maximum_lines]
            if not selected:
                break
            start_line = offset + 1
            end_line = offset + len(selected)
            identity = (
                f"{metadata.content_hash}:{start_line}:{end_line}:{self.parser_version}".encode()
            )
            chunks.append(
                SourceChunk(
                    chunk_id=hashlib.sha256(identity).hexdigest(),
                    path=metadata.path,
                    language=metadata.language,
                    start_line=start_line,
                    end_line=end_line,
                    content="\n".join(selected),
                )
            )
            if end_line == len(lines):
                break
        return tuple(chunks)
