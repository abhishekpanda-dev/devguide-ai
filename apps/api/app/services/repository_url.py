import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from app.core.exceptions import InvalidRepositoryUrlError

_MALFORMED_PERCENT_ENCODING = re.compile(r"%(?![0-9A-Fa-f]{2})")


@dataclass(frozen=True, slots=True)
class NormalizedRepositoryUrl:
    source_url: str
    normalized_url: str
    owner: str
    name: str


def normalize_repository_url(source_url: str) -> NormalizedRepositoryUrl:
    value = source_url.strip()
    if not value or _MALFORMED_PERCENT_ENCODING.search(value) or "\\" in value:
        raise InvalidRepositoryUrlError()

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise InvalidRepositoryUrlError() from exc

    if parsed.scheme.lower() != "https" or parsed.hostname is None:
        raise InvalidRepositoryUrlError("Only HTTPS GitHub repository URLs are supported.")
    if parsed.username is not None or parsed.password is not None or port is not None:
        raise InvalidRepositoryUrlError()
    if parsed.hostname.lower() != "github.com":
        raise InvalidRepositoryUrlError("Only github.com repository URLs are supported.")
    if parsed.query or parsed.fragment:
        raise InvalidRepositoryUrlError("Repository URLs cannot contain a query or fragment.")

    path = parsed.path[:-1] if parsed.path.endswith("/") else parsed.path
    encoded_parts = path.split("/")
    if len(encoded_parts) != 3 or encoded_parts[0] != "":
        raise InvalidRepositoryUrlError("The URL must identify one repository.")

    owner = unquote(encoded_parts[1])
    name = unquote(encoded_parts[2])
    if name.endswith(".git"):
        name = name[:-4]
    if (
        not owner
        or not name
        or len(owner) > 255
        or len(name) > 255
        or owner in {".", ".."}
        or name in {".", ".."}
        or any(character in owner or character in name for character in ("/", "\\", "\x00"))
    ):
        raise InvalidRepositoryUrlError()

    normalized_url = f"https://github.com/{owner}/{name}"
    return NormalizedRepositoryUrl(
        source_url=value,
        normalized_url=normalized_url,
        owner=owner,
        name=name,
    )
