import hashlib
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID, uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationValidationError, PersistenceError
from app.models import AnalysisParseMetadata, CodeChunk, RepositoryFile
from app.parser import RepositoryParseResult
from app.repositories import AnalysisJobRepository, ParsedRepository, RepositoryRepository
from app.schemas import ParserPersistenceResult


class ParserPersistenceService:
    def __init__(self, session: AsyncSession, repository: ParsedRepository | None = None) -> None:
        self._session = session
        self._repository = repository or ParsedRepository(session)

    async def persist(
        self,
        *,
        repository_id: UUID,
        analysis_job_id: UUID,
        commit_sha: str,
        result: RepositoryParseResult,
    ) -> ParserPersistenceResult:
        job = await AnalysisJobRepository(self._session).get_by_id(analysis_job_id)
        repository = await RepositoryRepository(self._session).get_by_id(repository_id)
        if (
            job is None
            or repository is None
            or job.repository_id != repository_id
            or repository.latest_commit_sha != commit_sha
        ):
            raise ApplicationValidationError("Parser persistence scope is invalid.")
        files: list[RepositoryFile] = []
        file_ids: dict[str, UUID] = {}
        for source in result.files:
            metadata = source.metadata
            path = PurePosixPath(metadata.path)
            if (
                path.is_absolute()
                or PureWindowsPath(metadata.path).is_absolute()
                or ".." in path.parts
            ):
                raise ApplicationValidationError("Parser output contains an invalid path.")
            model = RepositoryFile(
                id=uuid4(),
                repository_id=repository_id,
                analysis_job_id=analysis_job_id,
                commit_sha=commit_sha,
                path=metadata.path,
                file_name=metadata.file_name,
                extension=metadata.extension,
                language=metadata.language,
                size_bytes=metadata.size_bytes,
                line_count=metadata.line_count,
                content_hash=metadata.content_hash,
                is_test=metadata.is_test,
                is_documentation=metadata.is_documentation,
                is_configuration=metadata.is_configuration,
                is_generated=metadata.is_generated,
                encoding=metadata.encoding,
                limitations=list(metadata.limitations),
            )
            files.append(model)
            file_ids[metadata.path] = model.id
        chunks = [
            CodeChunk(
                id=chunk.chunk_id,
                repository_file_id=file_ids[chunk.path],
                analysis_job_id=analysis_job_id,
                commit_sha=commit_sha,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                language=chunk.language,
                parser_version=result.statistics.parser_version,
                content_hash=hashlib.sha256(chunk.content.encode()).hexdigest(),
            )
            for chunk in result.chunks
        ]
        try:
            await self._repository.replace(
                analysis_job_id,
                files,
                chunks,
                AnalysisParseMetadata(
                    analysis_job_id=analysis_job_id,
                    skipped_file_count=result.statistics.skipped_files,
                    limitations=list(result.statistics.limitations),
                ),
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc
        return ParserPersistenceResult(
            repository_id=repository_id,
            analysis_job_id=analysis_job_id,
            commit_sha=commit_sha,
            files_persisted=len(files),
            chunks_persisted=len(chunks),
        )
