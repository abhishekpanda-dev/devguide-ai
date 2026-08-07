from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CodeChunk, RepositoryFile


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
