import asyncio
from collections.abc import Awaitable, Coroutine
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from app.core.exceptions import (
    GitNotAvailableError,
    RepositoryCloneFailedError,
    RepositoryCloneTimeoutError,
)
from app.ingestion.git_runner import GitCommandRunner


class FakeProcess:
    def __init__(self, *, return_code: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> None:
        self.returncode: int | None = return_code
        self.stdout = asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.stdout.feed_eof()
        self.stderr = asyncio.StreamReader()
        self.stderr.feed_data(stderr)
        self.stderr.feed_eof()
        self.killed = False

    async def wait(self) -> int:
        return self.returncode or 0

    def kill(self) -> None:
        self.killed = True


async def test_clone_command_is_shallow_non_recursive_and_never_uses_shell(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    async def fake_spawn(*arguments: str, **kwargs: object) -> FakeProcess:
        captured["arguments"] = arguments
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)
    runner = GitCommandRunner(executable="git", timeout_seconds=10, clone_depth=1)
    await runner.clone(
        "https://github.com/acme/project",
        tmp_path / "repository",
        tmp_path / "metadata",
    )

    arguments = captured["arguments"]
    kwargs = captured["kwargs"]
    assert isinstance(arguments, tuple)
    assert ("--depth", "1") == (
        arguments[arguments.index("--depth")],
        arguments[arguments.index("--depth") + 1],
    )
    assert "--no-recurse-submodules" in arguments
    assert "--recurse-submodules" not in arguments
    assert "shell" not in kwargs
    assert kwargs["stdin"] is asyncio.subprocess.DEVNULL
    assert "credential.helper=" in arguments
    assert "protocol.file.allow=never" in arguments


async def test_missing_git_is_translated(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    async def missing_spawn(*arguments: str, **kwargs: object) -> FakeProcess:
        raise FileNotFoundError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", missing_spawn)
    runner = GitCommandRunner(executable="missing-git", timeout_seconds=10, clone_depth=1)
    with pytest.raises(GitNotAvailableError):
        await runner.clone("https://github.com/acme/project", tmp_path / "repo", tmp_path)


async def test_clone_failure_is_translated(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    async def failed_spawn(*arguments: str, **kwargs: object) -> FakeProcess:
        return FakeProcess(return_code=1, stderr=b"safe failure")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", failed_spawn)
    runner = GitCommandRunner(executable="git", timeout_seconds=10, clone_depth=1)
    with pytest.raises(RepositoryCloneFailedError):
        await runner.clone("https://github.com/acme/project", tmp_path / "repo", tmp_path)


async def test_timeout_is_translated_and_process_is_killed(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    process = FakeProcess()

    async def fake_spawn(*arguments: str, **kwargs: object) -> FakeProcess:
        return process

    async def forced_timeout(
        awaitable: Awaitable[tuple[bytes, bytes]], **_kwargs: float
    ) -> tuple[bytes, bytes]:
        if isinstance(awaitable, Coroutine):
            awaitable.close()
        raise TimeoutError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)
    monkeypatch.setattr(asyncio, "wait_for", forced_timeout)
    runner = GitCommandRunner(executable="git", timeout_seconds=0.1, clone_depth=1)
    with pytest.raises(RepositoryCloneTimeoutError):
        await runner.clone("https://github.com/acme/project", tmp_path / "repo", tmp_path)
    assert process.killed is True


async def test_commit_and_default_branch_are_captured(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    outputs = iter(
        [
            FakeProcess(stdout=b"a" * 40 + b"\n"),
            FakeProcess(stdout=b"origin/main\n"),
        ]
    )

    async def fake_spawn(*arguments: str, **kwargs: object) -> FakeProcess:
        return next(outputs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)
    runner = GitCommandRunner(executable="git", timeout_seconds=10, clone_depth=1)
    assert await runner.resolve_head(tmp_path / "repo", tmp_path) == "a" * 40
    assert await runner.discover_default_branch(tmp_path / "repo", tmp_path) == "main"
