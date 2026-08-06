from pathlib import Path

IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "coverage",
        "target",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)

REJECTED_EXTENSIONS = frozenset(
    {
        ".7z",
        ".a",
        ".avi",
        ".bmp",
        ".bz2",
        ".class",
        ".dll",
        ".dylib",
        ".exe",
        ".gif",
        ".gz",
        ".ico",
        ".jar",
        ".jpeg",
        ".jpg",
        ".mov",
        ".mp3",
        ".mp4",
        ".o",
        ".pdf",
        ".png",
        ".rar",
        ".so",
        ".tar",
        ".wav",
        ".webm",
        ".webp",
        ".woff",
        ".woff2",
        ".zip",
    }
)


def is_ignored_directory(name: str) -> bool:
    return name.casefold() in IGNORED_DIRECTORIES


def is_explicitly_rejected(path: Path) -> bool:
    return path.suffix.casefold() in REJECTED_EXTENSIONS


def appears_binary(data: bytes) -> bool:
    return b"\x00" in data
