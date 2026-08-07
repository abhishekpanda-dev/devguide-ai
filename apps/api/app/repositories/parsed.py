from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CodeChunk, RepositoryFile


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    repository_file_id: UUID
    chunk_id: str
    analysis_job_id: UUID
    path: str
    language: str
    file_line_count: int
    start_line: int
    end_line: int
    content: str
    content_hash: str
    commit_sha: str
    limitations: tuple[str, ...]


class ParsedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace(
        self, analysis_job_id: UUID, files: list[RepositoryFile], chunks: list[CodeChunk]
    ) -> None:
        await self._session.execute(
            delete(CodeChunk).where(CodeChunk.analysis_job_id == analysis_job_id)
        )
        await self._session.execute(
            delete(RepositoryFile).where(RepositoryFile.analysis_job_id == analysis_job_id)
        )
        self._session.add_all(files)
        await self._session.flush()
        self._session.add_all(chunks)
        await self._session.flush()

    async def list_files(self, analysis_job_id: UUID) -> list[RepositoryFile]:
        return list(
            (
                await self._session.scalars(
                    select(RepositoryFile)
                    .where(RepositoryFile.analysis_job_id == analysis_job_id)
                    .order_by(RepositoryFile.path)
                )
            ).all()
        )

    async def list_chunks(self, analysis_job_id: UUID) -> list[CodeChunk]:
        return list(
            (
                await self._session.scalars(
                    select(CodeChunk)
                    .where(CodeChunk.analysis_job_id == analysis_job_id)
                    .order_by(CodeChunk.repository_file_id, CodeChunk.start_line)
                )
            ).all()
        )

    async def search_candidates(
        self,
        analysis_job_id: UUID,
        *,
        languages: tuple[str, ...] = (),
        path_prefix: str | None = None,
    ) -> list[SearchCandidate]:
        """Return only persisted candidates inside one analysis scope.

        Filters are applied in the data-access layer so callers cannot accidentally rank
        chunks belonging to another analysis or outside the requested filter scope.
        """
        statement = (
            select(CodeChunk, RepositoryFile)
            .join(
                RepositoryFile,
                (RepositoryFile.id == CodeChunk.repository_file_id)
                & (RepositoryFile.analysis_job_id == CodeChunk.analysis_job_id),
            )
            .where(
                CodeChunk.analysis_job_id == analysis_job_id,
                RepositoryFile.analysis_job_id == analysis_job_id,
                CodeChunk.commit_sha == RepositoryFile.commit_sha,
            )
        )
        if languages:
            statement = statement.where(RepositoryFile.language.in_(languages))
        if path_prefix is not None:
            statement = statement.where(RepositoryFile.path.startswith(path_prefix))
        statement = statement.order_by(
            RepositoryFile.path,
            CodeChunk.start_line,
            CodeChunk.end_line,
            CodeChunk.id,
        )
        rows = (await self._session.execute(statement)).all()
        return [
            SearchCandidate(
                repository_file_id=file.id,
                chunk_id=chunk.id,
                analysis_job_id=chunk.analysis_job_id,
                path=file.path,
                language=file.language,
                file_line_count=file.line_count,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                content_hash=chunk.content_hash,
                commit_sha=chunk.commit_sha,
                limitations=tuple(file.limitations),
            )
            for chunk, file in rows
        ]
