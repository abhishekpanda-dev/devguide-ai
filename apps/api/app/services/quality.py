from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AnalysisNotFoundError, AnalysisNotReadyError, PersistenceError
from app.quality import QualityAnalysisResult
from app.repositories import AnalysisJobRepository, RepositoryRepository
from app.repositories.quality import RepositoryQualityRepository
from app.schemas.quality import (
    DuplicateGroupRead,
    DuplicateMemberRead,
    QualityResponse,
    ScoreDeductionRead,
    UnusedCandidateRead,
)
from app.services.finding import CodeFindingService


class RepositoryQualityPersistenceService:
    def __init__(
        self, session: AsyncSession, repository: RepositoryQualityRepository | None = None
    ) -> None:
        self.session = session
        self.repository = repository or RepositoryQualityRepository(session)

    async def persist(
        self, analysis_id: UUID, commit_sha: str, result: QualityAnalysisResult
    ) -> None:
        try:
            await self.repository.replace(analysis_id, commit_sha, result)
            await self.session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self.session.rollback()
            raise PersistenceError from exc


class RepositoryQualityService:
    def __init__(
        self,
        jobs: AnalysisJobRepository,
        repositories: RepositoryRepository,
        quality: RepositoryQualityRepository,
    ) -> None:
        self.jobs, self.repositories, self.quality = jobs, repositories, quality

    async def get_required(
        self, analysis_id: UUID, *, language: str | None, path_prefix: str | None, limit: int
    ) -> QualityResponse:
        analysis = await self.jobs.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError
        repository = await self.repositories.get_by_id(analysis.repository_id)
        if repository is None:
            raise AnalysisNotFoundError
        prefix = CodeFindingService.validate_prefix(path_prefix)
        record = await self.quality.get(
            analysis_id, language=language, path_prefix=prefix, limit=limit
        )
        if record is None:
            raise AnalysisNotReadyError
        unused = [
            UnusedCandidateRead(
                id=item.id,
                symbol_name=item.symbol_name,
                symbol_kind=item.symbol_kind,
                path=item.path,
                language=item.language,
                start_line=item.start_line,
                end_line=item.end_line,
                reason=item.reason,
                confidence=item.confidence,
                recommendation=item.recommendation,
                excerpt=item.excerpt,
                source_url=CodeFindingService.source_url(
                    repository.normalized_url,
                    item.commit_sha,
                    item.path,
                    item.start_line,
                    item.end_line,
                ),
            )
            for item in record.unused
        ]
        groups = [
            DuplicateGroupRead(
                group_id=group.id,
                confidence=group.confidence,
                recommendation=group.recommendation,
                members=[
                    DuplicateMemberRead(
                        path=item.path,
                        language=item.language,
                        start_line=item.start_line,
                        end_line=item.end_line,
                        excerpt=item.excerpt,
                        source_url=CodeFindingService.source_url(
                            repository.normalized_url,
                            item.commit_sha,
                            item.path,
                            item.start_line,
                            item.end_line,
                        ),
                    )
                    for item in members
                ],
            )
            for group, members in record.groups
        ]
        return QualityResponse(
            analysis_job_id=analysis_id,
            overall_score=record.metadata.overall_score,
            category_scores=record.metadata.category_scores,
            score_breakdown=[
                ScoreDeductionRead.model_validate(item) for item in record.metadata.deductions
            ],
            unused_code_candidates=unused,
            duplicate_code_groups=groups,
            summary={"unused_candidate_count": len(unused), "duplicate_group_count": len(groups)},
            limitations=record.metadata.limitations,
            score_version=record.metadata.score_version,
        )
