import pytest

from app.core.exceptions import InvalidRepositoryUrlError
from app.services.repository_url import normalize_repository_url


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "https://github.com/Owner/Repository",
            "https://github.com/Owner/Repository",
        ),
        (
            "https://github.com/owner/repository/",
            "https://github.com/owner/repository",
        ),
        (
            "https://github.com/owner/repository.git",
            "https://github.com/owner/repository",
        ),
    ],
)
def test_valid_repository_urls_are_normalized(source: str, expected: str) -> None:
    result = normalize_repository_url(source)
    assert result.normalized_url == expected
    assert result.owner == expected.split("/")[-2]
    assert result.name == expected.split("/")[-1]


@pytest.mark.parametrize(
    "source",
    [
        "http://github.com/owner/repository",
        "git@github.com:owner/repository.git",
        "ssh://git@github.com/owner/repository.git",
        "file:///owner/repository",
        "https://gitlab.com/owner/repository",
        "https://localhost/owner/repository",
        "https://127.0.0.1/owner/repository",
        "https://user:password@github.com/owner/repository",
        "https://github.com/owner/repository/tree/main",
        "https://github.com/owner/repository?tab=readme",
        "https://github.com/owner/repository#readme",
        "https://github.com/owner/",
        "https://github.com//repository",
        "not a URL",
        "https://github.com/owner/repo%ZZ",
        "https://github.com/owner/%2E%2E",
    ],
)
def test_unsafe_or_unsupported_repository_urls_are_rejected(source: str) -> None:
    with pytest.raises(InvalidRepositoryUrlError) as error:
        normalize_repository_url(source)
    assert error.value.code == "invalid_repository_url"
