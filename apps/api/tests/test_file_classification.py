import pytest

from app.parser.classification import FileClassification, classify_file


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("package-lock.json", FileClassification.LOCKFILE),
        ("npm-shrinkwrap.json", FileClassification.LOCKFILE),
        ("Pipfile.lock", FileClassification.LOCKFILE),
        ("node_modules/pkg/index.js", FileClassification.VENDOR),
        ("vendor/pkg/source.py", FileClassification.VENDOR),
        ("dist/bundle.js", FileClassification.BUILD_OUTPUT),
        (".next/server.js", FileClassification.BUILD_OUTPUT),
        ("generated/client.py", FileClassification.GENERATED),
        ("assets/app.min.js", FileClassification.MINIFIED),
        ("config/settings.json", FileClassification.CONFIGURATION),
        ("src/app.py", FileClassification.SOURCE),
    ],
)
def test_central_file_classification(path: str, expected: FileClassification) -> None:
    assert (
        classify_file(
            path,
            language="python" if path.endswith(".py") else "json",
            is_configuration=path.endswith(".json") and path != "package-lock.json",
        )
        is expected
    )


def test_generated_marker_and_traversal_safety() -> None:
    assert (
        classify_file(
            "src/client.py", language="python", content_prefix="# Code generated; DO NOT EDIT"
        )
        is FileClassification.GENERATED
    )
    with pytest.raises(ValueError):
        classify_file("../outside.py", language="python")
