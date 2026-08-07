from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.findings import FindingCandidate
from app.models import (
    AnalysisFindingsMetadata,
    CodeFinding,
    FindingCategory,
    FindingSeverity,
    RepositoryFile,
)


@dataclass(frozen=True, slots=True)
class FindingsPage:
    total_count: int
    findings: tuple[CodeFinding, ...]
    limitations: tuple[str, ...]
    severity_counts: dict[FindingSeverity, int]


class CodeFindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace(
        self,
        analysis_job_id: UUID,
        candidates: tuple[FindingCandidate, ...],
        limitations: tuple[str, ...],
    ) -> None:
        rows = (
            await self.session.execute(
                select(RepositoryFile.path, RepositoryFile.id).where(
                    RepositoryFile.analysis_job_id == analysis_job_id
                )
            )
        ).all()
        ids = {p: i for p, i in rows}
        if any(x.path not in ids for x in candidates):
            raise ValueError("finding file scope is invalid")
        await self.session.execute(
            delete(CodeFinding).where(CodeFinding.analysis_job_id == analysis_job_id)
        )
        await self.session.execute(
            delete(AnalysisFindingsMetadata).where(
                AnalysisFindingsMetadata.analysis_job_id == analysis_job_id
            )
        )
        self.session.add_all(
            [
                CodeFinding(
                    analysis_job_id=analysis_job_id,
                    repository_file_id=ids[x.path],
                    rule_id=x.rule_id,
                    severity=x.severity,
                    category=x.category,
                    title=x.title,
                    explanation=x.explanation,
                    path=x.path,
                    start_line=x.start_line,
                    end_line=x.end_line,
                    evidence_excerpt=x.evidence_excerpt,
                    deterministic_recommendation=x.deterministic_recommendation,
                    confidence=x.confidence,
                    content_hash=x.content_hash,
                    commit_sha=x.commit_sha,
                )
                for x in candidates
            ]
        )
        self.session.add(
            AnalysisFindingsMetadata(analysis_job_id=analysis_job_id, limitations=list(limitations))
        )
        await self.session.flush()

    async def list_for_analysis(
        self,
        analysis_job_id: UUID,
        *,
        severity: FindingSeverity | None = None,
        category: FindingCategory | None = None,
        path_prefix: str | None = None,
        limit: int = 50,
    ) -> FindingsPage | None:
        metadata = await self.session.scalar(
            select(AnalysisFindingsMetadata).where(
                AnalysisFindingsMetadata.analysis_job_id == analysis_job_id
            )
        )
        if metadata is None:
            return None
        filters = [CodeFinding.analysis_job_id == analysis_job_id]
        if severity is not None:
            filters.append(CodeFinding.severity == severity)
        if category is not None:
            filters.append(CodeFinding.category == category)
        if path_prefix is not None:
            filters.append(CodeFinding.path.startswith(path_prefix))
        total = await self.session.scalar(select(func.count(CodeFinding.id)).where(*filters))
        query = (
            select(CodeFinding)
            .where(*filters)
            .order_by(
                CodeFinding.path,
                CodeFinding.start_line,
                CodeFinding.end_line,
                CodeFinding.rule_id,
                CodeFinding.id,
            )
            .limit(limit)
        )
        findings = tuple((await self.session.scalars(query)).all())
        counts = (
            await self.session.execute(
                select(CodeFinding.severity, func.count(CodeFinding.id))
                .where(CodeFinding.analysis_job_id == analysis_job_id)
                .group_by(CodeFinding.severity)
            )
        ).all()
        return FindingsPage(
            int(total or 0), findings, tuple(metadata.limitations), {s: int(n) for s, n in counts}
        )
