import hashlib
import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from app.parser import RepositoryParser, TextChunker, detect_language
from app.parser.metadata import build_metadata
from app.parser.types import SourceFileMetadata


@pytest.mark.parametrize(
    ("name", "language"),
    [
        ("main.py", "python"),
        ("main.js", "javascript"),
        ("main.jsx", "javascript"),
        ("main.ts", "typescript"),
        ("main.java", "java"),
        ("index.html", "html"),
        ("style.css", "css"),
        ("data.json", "json"),
        ("config.yml", "yaml"),
        ("README.md", "markdown"),
        ("pyproject.toml", "toml"),
        ("program.rs", None),
    ],
)
def test_extension_language_detection(name: str, language: str | None) -> None:
    assert detect_language(name) == language


def metadata(content: str = "one\ntwo\n") -> SourceFileMetadata:
    data = content.encode()
    return build_metadata(
        relative_path="src/main.py",
        language="python",
        data=data,
        content=content,
        encoding="utf-8",
    )


def test_small_file_creates_one_chunk_with_inclusive_lines() -> None:
    item = metadata()
    chunks = TextChunker(maximum_lines=200, overlap_lines=20).chunk(item, "one\ntwo\n")
    assert len(chunks) == 1
    assert (chunks[0].start_line, chunks[0].end_line) == (1, 2)
    assert chunks[0].content == "one\ntwo"


def test_large_file_chunks_with_overlap_and_stable_ids() -> None:
    content = "\n".join(f"line-{index}" for index in range(1, 8))
    item = metadata(content)
    chunker = TextChunker(maximum_lines=3, overlap_lines=1, parser_version="v1")
    first = chunker.chunk(item, content)
    second = chunker.chunk(item, content)
    assert [(chunk.start_line, chunk.end_line) for chunk in first] == [(1, 3), (3, 5), (5, 7)]
    assert first[0].content.splitlines()[-1] == first[1].content.splitlines()[0]
    assert first == second
    assert all(chunk.content and chunk.start_line <= chunk.end_line for chunk in first)


@pytest.mark.parametrize(
    ("maximum", "overlap"),
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_chunk_configuration_is_rejected(maximum: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        TextChunker(maximum_lines=maximum, overlap_lines=overlap)


def test_parser_filters_files_and_builds_metadata_and_statistics(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('safe')\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    test_data = "def test_value():\n    assert True\n"
    (tmp_path / "tests" / "test_main.py").write_text(test_data, encoding="utf-8")
    (tmp_path / "README.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "unsupported.rs").write_text("fn main() {}", encoding="utf-8")
    (tmp_path / "binary.py").write_bytes(b"safe\x00binary")
    (tmp_path / "image.png").write_bytes(b"image")
    (tmp_path / "archive.zip").write_bytes(b"archive")
    (tmp_path / "program.exe").write_bytes(b"program")
    (tmp_path / "large.ts").write_bytes(b"x" * 101)
    ignored = tmp_path / "node_modules"
    ignored.mkdir()
    (ignored / "dependency.js").write_text("executed = True", encoding="utf-8")

    result = RepositoryParser(maximum_file_size_bytes=100).parse(tmp_path)

    assert [item.metadata.path for item in result.files] == [
        "README.md",
        "config.json",
        "src/main.py",
        "tests/test_main.py",
    ]
    test_file = result.files[-1].metadata
    assert test_file.file_name == "test_main.py"
    assert test_file.extension == ".py"
    assert test_file.language == "python"
    assert test_file.line_count == 2
    assert (
        test_file.content_hash
        == hashlib.sha256((tmp_path / "tests" / "test_main.py").read_bytes()).hexdigest()
    )
    assert test_file.is_test is True
    assert result.files[0].metadata.is_documentation is True
    assert result.files[1].metadata.is_configuration is True
    stats = result.statistics
    assert stats.total_files_discovered == 10
    assert stats.accepted_source_files == 4
    assert stats.skipped_files == 6
    assert stats.skipped_directories == 1
    assert stats.file_count_by_language == {"json": 1, "markdown": 1, "python": 2}
    assert stats.line_count_by_language == {"json": 1, "markdown": 1, "python": 3}
    assert stats.total_accepted_lines == 5
    assert stats.total_accepted_bytes == sum(item.metadata.size_bytes for item in result.files)
    assert stats.largest_accepted_file == "tests/test_main.py"
    assert stats.smallest_accepted_file == "config.json"
    assert stats.documentation_file_count == 1
    assert stats.configuration_file_count == 1
    assert stats.test_file_count == 1
    assert stats.total_chunks == 4


def test_output_order_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "z.py").write_text("z\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("a\n", encoding="utf-8")
    parser = RepositoryParser(maximum_lines_per_chunk=1, overlap_lines=0)
    first = parser.parse(tmp_path)
    second = parser.parse(tmp_path)
    assert first == second
    assert [item.metadata.path for item in first.files] == ["a.py", "z.py"]
    assert [item.path for item in first.chunks] == ["a.py", "z.py"]


def test_unreadable_file_is_skipped_with_limitation(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    blocked = tmp_path / "blocked.py"
    blocked.write_text("safe = True", encoding="utf-8")
    original = Path.read_bytes

    def fail_selected(path: Path) -> bytes:
        if path == blocked:
            raise PermissionError
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", fail_selected)
    result = RepositoryParser().parse(tmp_path)
    assert result.files == ()
    assert result.statistics.skipped_files == 1
    assert result.statistics.limitations == ("blocked.py: file could not be read.",)


def test_symlinks_are_never_followed(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("outside = True", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        os.symlink(outside, link)
    except OSError:
        original = Path.is_symlink

        def report_root_as_symlink(path: Path) -> bool:
            return path == tmp_path or original(path)

        monkeypatch.setattr(Path, "is_symlink", report_root_as_symlink)
        with pytest.raises(ValueError, match="symbolic link"):
            RepositoryParser().parse(tmp_path)
        return
    result = RepositoryParser().parse(tmp_path)
    assert result.files == ()
    assert result.statistics.skipped_files == 1
    assert "symbolic link was skipped" in result.statistics.limitations[0]


def test_repository_root_must_be_a_real_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "file.py"
    file_path.write_text("safe = True", encoding="utf-8")
    with pytest.raises(ValueError):
        RepositoryParser().parse(file_path)
