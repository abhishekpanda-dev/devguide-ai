from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    AnalysisStructureMetadata,
    RepositoryDependencyEdge,
    RepositoryFile,
    RepositoryFileIntelligence,
)
from app.parser.classification import classify_file
from app.structure import StructureAnalysisResult


@dataclass(frozen=True, slots=True)
class StructureRecord:
    metadata: AnalysisStructureMetadata
    files: tuple[tuple[RepositoryFile, RepositoryFileIntelligence], ...]
    edges: tuple[RepositoryDependencyEdge, ...]


class RepositoryStructureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace(self, analysis_id: UUID, result: StructureAnalysisResult) -> None:
        files = list(
            (
                await self.session.scalars(
                    select(RepositoryFile).where(RepositoryFile.analysis_job_id == analysis_id)
                )
            ).all()
        )
        by_path = {item.path: item for item in files}
        if any(
            edge.source_path not in by_path or edge.target_path not in by_path
            for edge in result.edges
        ):
            raise ValueError("structure edge file scope is invalid")
        await self.session.execute(
            delete(RepositoryDependencyEdge).where(
                RepositoryDependencyEdge.analysis_job_id == analysis_id
            )
        )
        await self.session.execute(
            delete(RepositoryFileIntelligence).where(
                RepositoryFileIntelligence.analysis_job_id == analysis_id
            )
        )
        await self.session.execute(
            delete(AnalysisStructureMetadata).where(
                AnalysisStructureMetadata.analysis_job_id == analysis_id
            )
        )
        inbound = {path: 0 for path in by_path}
        outbound = {path: 0 for path in by_path}
        edge_models = []
        for edge in result.edges:
            inbound[edge.target_path] += 1
            outbound[edge.source_path] += 1
            edge_models.append(
                RepositoryDependencyEdge(
                    analysis_job_id=analysis_id,
                    source_repository_file_id=by_path[edge.source_path].id,
                    target_repository_file_id=by_path[edge.target_path].id,
                    relationship_type=edge.relationship_type,
                    module_name=edge.module_name,
                    source_path=edge.source_path,
                    target_path=edge.target_path,
                    source_line=edge.source_line,
                    confidence=edge.confidence,
                )
            )
        entry_by_path = {item.path: item for item in result.entry_points}
        intelligence = []
        for path, file in by_path.items():
            entry = entry_by_path.get(path)
            classification = classify_file(
                path,
                language=file.language,
                is_test=file.is_test,
                is_documentation=file.is_documentation,
                is_configuration=file.is_configuration,
                is_generated=file.is_generated,
            )
            intelligence.append(
                RepositoryFileIntelligence(
                    analysis_job_id=analysis_id,
                    repository_file_id=file.id,
                    classification=classification.value,
                    is_entry_point=entry is not None,
                    entry_point_reason=entry.reason if entry else None,
                    entry_point_confidence=entry.confidence if entry else 0,
                    inbound_dependency_count=inbound[path],
                    outbound_dependency_count=outbound[path],
                )
            )
        self.session.add_all(
            (
                *edge_models,
                *intelligence,
                AnalysisStructureMetadata(
                    analysis_job_id=analysis_id, limitations=list(result.limitations)
                ),
            )
        )
        await self.session.flush()

    async def get(
        self,
        analysis_id: UUID,
        *,
        edge_limit: int | None = None,
        related_paths: tuple[str, ...] = (),
    ) -> StructureRecord | None:
        metadata = await self.session.scalar(
            select(AnalysisStructureMetadata).where(
                AnalysisStructureMetadata.analysis_job_id == analysis_id
            )
        )
        if metadata is None:
            return None
        rows = (
            await self.session.execute(
                select(RepositoryFile, RepositoryFileIntelligence)
                .join(
                    RepositoryFileIntelligence,
                    (RepositoryFileIntelligence.repository_file_id == RepositoryFile.id)
                    & (
                        RepositoryFileIntelligence.analysis_job_id == RepositoryFile.analysis_job_id
                    ),
                )
                .where(RepositoryFile.analysis_job_id == analysis_id)
                .order_by(RepositoryFile.path)
            )
        ).all()
        edge_query = select(RepositoryDependencyEdge).where(
            RepositoryDependencyEdge.analysis_job_id == analysis_id
        )
        if related_paths:
            path_filters: list[ColumnElement[bool]] = []
            for path in related_paths:
                path_filters.extend(
                    (
                        RepositoryDependencyEdge.source_path == path,
                        RepositoryDependencyEdge.target_path == path,
                        RepositoryDependencyEdge.source_path.endswith(f"/{path}"),
                        RepositoryDependencyEdge.target_path.endswith(f"/{path}"),
                    )
                )
            edge_query = edge_query.where(or_(*path_filters))
        edge_query = edge_query.order_by(
            RepositoryDependencyEdge.source_path,
            RepositoryDependencyEdge.source_line,
            RepositoryDependencyEdge.target_path,
        )
        if edge_limit is not None:
            edge_query = edge_query.limit(edge_limit)
        edges = tuple((await self.session.scalars(edge_query)).all())
        return StructureRecord(metadata, tuple((row[0], row[1]) for row in rows), edges)

    async def dependencies_of(
        self, analysis_id: UUID, file_id: UUID
    ) -> tuple[RepositoryDependencyEdge, ...]:
        return tuple(
            (
                await self.session.scalars(
                    select(RepositoryDependencyEdge)
                    .where(
                        RepositoryDependencyEdge.analysis_job_id == analysis_id,
                        RepositoryDependencyEdge.source_repository_file_id == file_id,
                    )
                    .order_by(RepositoryDependencyEdge.target_path)
                )
            ).all()
        )

    async def dependents_of(
        self, analysis_id: UUID, file_id: UUID
    ) -> tuple[RepositoryDependencyEdge, ...]:
        return tuple(
            (
                await self.session.scalars(
                    select(RepositoryDependencyEdge)
                    .where(
                        RepositoryDependencyEdge.analysis_job_id == analysis_id,
                        RepositoryDependencyEdge.target_repository_file_id == file_id,
                    )
                    .order_by(RepositoryDependencyEdge.source_path)
                )
            ).all()
        )

    async def probable_entry_points(
        self, analysis_id: UUID
    ) -> tuple[RepositoryFileIntelligence, ...]:
        return tuple(
            (
                await self.session.scalars(
                    select(RepositoryFileIntelligence)
                    .where(
                        RepositoryFileIntelligence.analysis_job_id == analysis_id,
                        RepositoryFileIntelligence.is_entry_point.is_(True),
                    )
                    .order_by(RepositoryFileIntelligence.repository_file_id)
                )
            ).all()
        )

    async def most_connected(
        self, analysis_id: UUID, *, limit: int
    ) -> tuple[RepositoryFileIntelligence, ...]:
        total = (
            RepositoryFileIntelligence.inbound_dependency_count
            + RepositoryFileIntelligence.outbound_dependency_count
        )
        return tuple(
            (
                await self.session.scalars(
                    select(RepositoryFileIntelligence)
                    .where(RepositoryFileIntelligence.analysis_job_id == analysis_id)
                    .order_by(desc(total), RepositoryFileIntelligence.repository_file_id)
                    .limit(limit)
                )
            ).all()
        )

    async def files_by_language(
        self, analysis_id: UUID, language: str
    ) -> tuple[RepositoryFile, ...]:
        return tuple(
            (
                await self.session.scalars(
                    select(RepositoryFile)
                    .where(
                        RepositoryFile.analysis_job_id == analysis_id,
                        RepositoryFile.language == language,
                    )
                    .order_by(RepositoryFile.path)
                )
            ).all()
        )

    async def files_under_prefix(
        self, analysis_id: UUID, prefix: str
    ) -> tuple[RepositoryFile, ...]:
        return tuple(
            (
                await self.session.scalars(
                    select(RepositoryFile)
                    .where(
                        RepositoryFile.analysis_job_id == analysis_id,
                        RepositoryFile.path.startswith(prefix),
                    )
                    .order_by(RepositoryFile.path)
                )
            ).all()
        )
