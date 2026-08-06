import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.exceptions import (
    GitNotAvailableError,
    RepositoryCloneFailedError,
    RepositoryCloneTimeoutError,
)

_MAX_CAPTURE_BYTES = 64 * 1024


class GitRunner(Protocol):
    async def clone(self, repository_url: str, destination: Path, metadata_path: Path) -> None: ...

    async def resolve_head(self, repository_path: Path, metadata_path: Path) -> str: ...

    async def discover_default_branch(
        self, repository_path: Path, metadata_path: Path
    ) -> str | None: ...


@dataclass(frozen=True, slots=True)
class _CommandResult:
    return_code: int
    stdout: str
    stderr: str


class GitCommandRunner:
    def __init__(self, *, executable: str, timeout_seconds: float, clone_depth: int) -> None:
        if clone_depth != 1:
            raise ValueError("only clone depth 1 is supported")
        self._executable = executable
        self._timeout_seconds = timeout_seconds
        self._clone_depth = clone_depth

    async def clone(self, repository_url: str, destination: Path, metadata_path: Path) -> None:
        result = await self._run(
            (
                "-c",
                f"core.hooksPath={metadata_path / 'disabled-hooks'}",
                "-c",
                "credential.helper=",
                "-c",
                "protocol.file.allow=never",
                "-c",
                "protocol.ext.allow=never",
                "clone",
                "--depth",
                str(self._clone_depth),
                "--no-tags",
                "--no-recurse-submodules",
                "--single-branch",
                "--no-local",
                "--",
                repository_url,
                str(destination),
            ),
            metadata_path=metadata_path,
        )
        if result.return_code != 0:
            raise RepositoryCloneFailedError

    async def resolve_head(self, repository_path: Path, metadata_path: Path) -> str:
        result = await self._run(
            ("-C", str(repository_path), "rev-parse", "HEAD"),
            metadata_path=metadata_path,
        )
        if result.return_code != 0 or not result.stdout.strip():
            raise RepositoryCloneFailedError
        return result.stdout.strip()

    async def discover_default_branch(
        self, repository_path: Path, metadata_path: Path
    ) -> str | None:
        result = await self._run(
            (
                "-C",
                str(repository_path),
                "symbolic-ref",
                "--short",
                "refs/remotes/origin/HEAD",
            ),
            metadata_path=metadata_path,
        )
        if result.return_code != 0:
            return None
        branch = result.stdout.strip()
        if branch.startswith("origin/"):
            branch = branch.removeprefix("origin/")
        if not branch or len(branch) > 255 or any(character in branch for character in "\r\n\x00"):
            return None
        return branch

    async def _run(self, arguments: tuple[str, ...], *, metadata_path: Path) -> _CommandResult:
        environment = _git_environment(metadata_path)
        try:
            process = await asyncio.create_subprocess_exec(
                self._executable,
                *arguments,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=environment,
            )
        except FileNotFoundError as exc:
            raise GitNotAvailableError from exc
        except OSError as exc:
            raise RepositoryCloneFailedError from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                _collect_process_output(process), timeout=self._timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise RepositoryCloneTimeoutError from exc

        return _CommandResult(
            return_code=process.returncode or 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )


async def _collect_process_output(process: asyncio.subprocess.Process) -> tuple[bytes, bytes]:
    if process.stdout is None or process.stderr is None:
        raise RepositoryCloneFailedError
    stdout_task = asyncio.create_task(_read_bounded(process.stdout))
    stderr_task = asyncio.create_task(_read_bounded(process.stderr))
    try:
        await process.wait()
        return await stdout_task, await stderr_task
    except BaseException:
        stdout_task.cancel()
        stderr_task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        raise


async def _read_bounded(stream: asyncio.StreamReader) -> bytes:
    captured = bytearray()
    while chunk := await stream.read(8192):
        remaining = _MAX_CAPTURE_BYTES - len(captured)
        if remaining > 0:
            captured.extend(chunk[:remaining])
    return bytes(captured)


def _git_environment(metadata_path: Path) -> dict[str, str]:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "Never",
        "HOME": str(metadata_path),
        "LANG": "C",
        "LC_ALL": "C",
    }
    for name in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
        if value := os.environ.get(name):
            environment[name] = value
    return environment
