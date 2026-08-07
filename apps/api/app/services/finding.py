from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import quote
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnalysisNotFoundError,
    ApplicationValidationError,
    CodeFindingsNotReadyError,
    PersistenceError,
)
from app.findings import FindingsAnalysisResult
from app.models import FindingCategory, FindingSeverity
from app.repositories import AnalysisJobRepository, CodeFindingRepository, RepositoryRepository
from app.schemas import CodeFindingRead, CodeFindingsResponse


class CodeFindingPersistenceService:
    def __init__(
        self, session: AsyncSession, repository: CodeFindingRepository | None = None
    ) -> None:
        self.session = session
        self.repository = repository or CodeFindingRepository(session)

    async def persist(self, analysis_job_id: UUID, result: FindingsAnalysisResult) -> None:
        try:
            await self.repository.replace(analysis_job_id, result.findings, result.limitations)
            await self.session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self.session.rollback()
            raise PersistenceError from exc


class CodeFindingService:
    def __init__(
        self,
        jobs: AnalysisJobRepository,
        repositories: RepositoryRepository,
        findings: CodeFindingRepository,
    ) -> None:
        self.jobs = jobs
        self.repositories = repositories
        self.findings = findings

    async def list_required(
        self,
        analysis_job_id: UUID,
        *,
        severity: FindingSeverity | None,
        category: FindingCategory | None,
        path_prefix: str | None,
        limit: int,
    ) -> CodeFindingsResponse:
        prefix = self.validate_prefix(path_prefix)
        try:
            analysis = await self.jobs.get_by_id(analysis_job_id)
            if analysis is None:
                raise AnalysisNotFoundError
            repository = await self.repositories.get_by_id(analysis.repository_id)
            if repository is None:
                raise AnalysisNotFoundError
            page = await self.findings.list_for_analysis(
                analysis_job_id,
                severity=severity,
                category=category,
                path_prefix=prefix,
                limit=limit,
            )
        except SQLAlchemyError as exc:
            raise PersistenceError from exc
        if page is None:
            raise CodeFindingsNotReadyError
        items = [
            CodeFindingRead(
                id=f.id,
                rule_id=f.rule_id,
                severity=f.severity,
                category=f.category,
                title=f.title,
                explanation=f.explanation,
                path=f.path,
                start_line=f.start_line,
                end_line=f.end_line,
                evidence_excerpt=f.evidence_excerpt,
                deterministic_recommendation=f.deterministic_recommendation,
                confidence=f.confidence,
                content_hash=f.content_hash,
                commit_sha=f.commit_sha,
                source_url=self.source_url(
                    repository.normalized_url, f.commit_sha, f.path, f.start_line, f.end_line
                ),
            )
            for f in page.findings
        ]
        return CodeFindingsResponse(
            analysis_job_id=analysis_job_id,
            total_count=page.total_count,
            returned_count=len(items),
            findings=items,
            limitations=list(page.limitations),
            severity_counts={s: page.severity_counts.get(s, 0) for s in FindingSeverity},
        )

    @staticmethod
    def validate_prefix(value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().replace("\\", "/").rstrip("/")
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or PureWindowsPath(value).is_absolute()
            or ".." in path.parts
        ):
            raise ApplicationValidationError("path_prefix must be repository-relative")
        return value

    @staticmethod
    def source_url(repository_url: str, sha: str, path_value: str, start: int, end: int) -> str:
        path = PurePosixPath(path_value)
        if (
            not path_value
            or "\\" in path_value
            or path.is_absolute()
            or PureWindowsPath(path_value).is_absolute()
            or ".." in path.parts
            or not sha
            or start < 1
            or end < start
        ):
            raise PersistenceError
        fragment = f"#L{start}" if start == end else f"#L{start}-L{end}"
        base = f"{repository_url.rstrip('/')}/blob/{quote(sha, safe='')}"
        return f"{base}/{quote(path_value, safe='/')}{fragment}"
