import hashlib
from pathlib import PurePosixPath

from app.parser.classification import FileClassification, classify_file
from app.parser.types import SourceFileMetadata

_CONFIG_NAMES = frozenset(
    {"package.json", "tsconfig.json", "pyproject.toml", "config.json", "config.yaml", "config.yml"}
)


def build_metadata(
    *, relative_path: str, language: str, data: bytes, content: str, encoding: str
) -> SourceFileMetadata:
    path = PurePosixPath(relative_path)
    lowered_parts = tuple(part.casefold() for part in path.parts)
    stem = path.stem.casefold()
    name = path.name.casefold()
    extension = path.suffix.casefold()
    line_count = len(content.splitlines())
    is_test = (
        any(part in {"test", "tests", "__tests__"} for part in lowered_parts[:-1])
        or stem.startswith("test_")
        or stem.endswith(("_test", ".test", ".spec"))
    )
    is_documentation = language == "markdown" or any(
        part in {"doc", "docs", "documentation"} for part in lowered_parts[:-1]
    )
    is_configuration = language in {"json", "yaml", "toml"} or name in _CONFIG_NAMES
    classification = classify_file(
        relative_path,
        language=language,
        is_test=is_test,
        is_documentation=is_documentation,
        is_configuration=is_configuration,
        content_prefix=content,
    )
    is_generated = classification in {
        FileClassification.GENERATED,
        FileClassification.BUILD_OUTPUT,
        FileClassification.VENDOR,
        FileClassification.MINIFIED,
    }
    return SourceFileMetadata(
        path=relative_path,
        file_name=path.name,
        extension=extension,
        language=language,
        size_bytes=len(data),
        line_count=line_count,
        content_hash=hashlib.sha256(data).hexdigest(),
        is_test=is_test,
        is_documentation=is_documentation,
        is_configuration=is_configuration,
        is_generated=is_generated,
        encoding=encoding,
    )
