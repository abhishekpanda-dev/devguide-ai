from collections import Counter
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnalysisNotFoundError,
    AnalysisNotReadyError,
    ApplicationValidationError,
    PersistenceError,
)
from app.models import RepositoryFile, RepositoryFileIntelligence
from app.repositories import (
    AnalysisJobRepository,
    RepositoryRepository,
    RepositoryStructureRepository,
)
from app.schemas.structure import (
    StructureEdgeRead,
    StructureFileRead,
    StructureRepositoryRead,
    StructureResponse,
    StructureSummary,
)
from app.services.finding import CodeFindingService
from app.structure import StructureAnalysisResult


class RepositoryStructurePersistenceService:
    def __init__(
        self, session: AsyncSession, repository: RepositoryStructureRepository | None = None
    ) -> None:
        self.session = session
        self.repository = repository or RepositoryStructureRepository(session)

    async def persist(self, analysis_id: UUID, result: StructureAnalysisResult) -> None:
        try:
            await self.repository.replace(analysis_id, result)
            await self.session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self.session.rollback()
            raise PersistenceError from exc


class RepositoryStructureService:
    def __init__(
        self,
        jobs: AnalysisJobRepository,
        repositories: RepositoryRepository,
        structures: RepositoryStructureRepository,
    ) -> None:
        self.jobs, self.repositories, self.structures = jobs, repositories, structures

    async def get_required(
        self,
        analysis_id: UUID,
        *,
        language: str | None,
        path_prefix: str | None,
        relationship_type: str | None,
        limit: int,
    ) -> StructureResponse:
        prefix = self._prefix(path_prefix)
        analysis = await self.jobs.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError
        repository = await self.repositories.get_by_id(analysis.repository_id)
        record = await self.structures.get(analysis_id)
        if repository is None:
            raise AnalysisNotFoundError
        if record is None:
            raise AnalysisNotReadyError
        all_files = [self._file(file, info) for file, info in record.files]
        selected_files = [
            item
            for item in all_files
            if (language is None or item.language == language)
            and (prefix is None or item.path.startswith(prefix))
        ]
        allowed_paths = {item.path for item in selected_files}
        filter_active = language is not None or prefix is not None
        file_by_path = {item.path: item for item in all_files}
        edges = [
            edge
            for edge in record.edges
            if (relationship_type is None or edge.relationship_type == relationship_type)
            and (
                not filter_active
                or edge.source_path in allowed_paths
                or edge.target_path in allowed_paths
            )
        ]
        edge_reads = [
            StructureEdgeRead(
                id=edge.id,
                source_repository_file_id=edge.source_repository_file_id,
                target_repository_file_id=edge.target_repository_file_id,
                relationship_type=edge.relationship_type,
                module_name=edge.module_name,
                source_path=edge.source_path,
                target_path=edge.target_path,
                source_line=edge.source_line,
                confidence=edge.confidence,
                source_url=CodeFindingService.source_url(
                    repository.normalized_url,
                    file_by_path[edge.source_path].commit_sha,
                    edge.source_path,
                    edge.source_line,
                    edge.source_line,
                ),
            )
            for edge in edges[:limit]
        ]
        languages = Counter(item.language for item in all_files)
        directories = {
            str(PurePosixPath(item.path).parent)
            for item in all_files
            if str(PurePosixPath(item.path).parent) != "."
        }
        connected = sorted(all_files, key=lambda item: (-item.total_dependency_count, item.path))
        summary = StructureSummary(
            file_count=len(all_files),
            directory_count=len(directories),
            language_counts=dict(sorted(languages.items())),
            edge_count=len(record.edges),
            entry_point_count=sum(item.is_entry_point for item in all_files),
            highest_inbound_files=sorted(
                all_files, key=lambda item: (-item.inbound_dependency_count, item.path)
            )[:5],
            highest_outbound_files=sorted(
                all_files, key=lambda item: (-item.outbound_dependency_count, item.path)
            )[:5],
            most_connected_files=connected[:5],
        )
        return StructureResponse(
            analysis_job_id=analysis_id,
            repository=StructureRepositoryRead(
                id=repository.id,
                owner=repository.owner,
                name=repository.name,
                commit_sha=all_files[0].commit_sha
                if all_files
                else repository.latest_commit_sha or "",
            ),
            files=selected_files[:limit],
            dependency_edges=edge_reads,
            entry_points=[item for item in all_files if item.is_entry_point],
            summary=summary,
            limitations=list(record.metadata.limitations),
        )

    @staticmethod
    def _file(file: RepositoryFile, info: RepositoryFileIntelligence) -> StructureFileRead:
        return StructureFileRead(
            repository_file_id=file.id,
            path=file.path,
            language=file.language,
            classification=info.classification,
            line_count=file.line_count,
            content_hash=file.content_hash,
            commit_sha=file.commit_sha,
            is_entry_point=info.is_entry_point,
            entry_point_reason=info.entry_point_reason,
            entry_point_confidence=info.entry_point_confidence,
            inbound_dependency_count=info.inbound_dependency_count,
            outbound_dependency_count=info.outbound_dependency_count,
            total_dependency_count=(info.inbound_dependency_count + info.outbound_dependency_count),
        )

    @staticmethod
    def _prefix(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().replace("\\", "/").rstrip("/")
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or PureWindowsPath(normalized).is_absolute()
            or ".." in path.parts
        ):
            raise ApplicationValidationError("path_prefix must be repository-relative")
        return f"{normalized}/"
