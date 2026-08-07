from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnalysisQualityMetadata,
    DuplicateCodeGroup,
    DuplicateCodeMember,
    RepositoryFile,
    UnusedCodeCandidateModel,
)
from app.quality import QualityAnalysisResult


@dataclass(frozen=True, slots=True)
class QualityRecord:
    metadata: AnalysisQualityMetadata
    unused: tuple[UnusedCodeCandidateModel, ...]
    groups: tuple[tuple[DuplicateCodeGroup, tuple[DuplicateCodeMember, ...]], ...]


class RepositoryQualityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace(
        self, analysis_id: UUID, commit_sha: str, result: QualityAnalysisResult
    ) -> None:
        files = {
            path: file_id
            for path, file_id in (
                await self.session.execute(
                    select(RepositoryFile.path, RepositoryFile.id).where(
                        RepositoryFile.analysis_job_id == analysis_id
                    )
                )
            ).all()
        }
        paths = [item.path for item in result.unused_candidates] + [
            member.path for group in result.duplicate_groups for member in group.members
        ]
        if any(path not in files for path in paths):
            raise ValueError("quality candidate file scope is invalid")
        await self.session.execute(
            delete(DuplicateCodeMember).where(DuplicateCodeMember.analysis_job_id == analysis_id)
        )
        await self.session.execute(
            delete(DuplicateCodeGroup).where(DuplicateCodeGroup.analysis_job_id == analysis_id)
        )
        await self.session.execute(
            delete(UnusedCodeCandidateModel).where(
                UnusedCodeCandidateModel.analysis_job_id == analysis_id
            )
        )
        await self.session.execute(
            delete(AnalysisQualityMetadata).where(
                AnalysisQualityMetadata.analysis_job_id == analysis_id
            )
        )
        self.session.add(
            AnalysisQualityMetadata(
                analysis_job_id=analysis_id,
                overall_score=result.overall_score,
                category_scores=result.category_scores,
                deductions=[
                    {
                        "category": d.category,
                        "signal_type": d.signal_type,
                        "count": d.count,
                        "points_deducted": d.points_deducted,
                        "explanation": d.explanation,
                    }
                    for d in result.deductions
                ],
                score_version=result.score_version,
                limitations=list(result.limitations),
            )
        )
        self.session.add_all(
            [
                UnusedCodeCandidateModel(
                    analysis_job_id=analysis_id,
                    repository_file_id=files[item.path],
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
                    commit_sha=commit_sha,
                )
                for item in result.unused_candidates
            ]
        )
        for group in result.duplicate_groups:
            self.session.add(
                DuplicateCodeGroup(
                    id=group.group_id,
                    analysis_job_id=analysis_id,
                    fingerprint=group.fingerprint,
                    confidence=group.confidence,
                    recommendation=group.recommendation,
                )
            )
            self.session.add_all(
                [
                    DuplicateCodeMember(
                        analysis_job_id=analysis_id,
                        group_id=group.group_id,
                        repository_file_id=files[item.path],
                        path=item.path,
                        language=item.language,
                        start_line=item.start_line,
                        end_line=item.end_line,
                        excerpt=item.excerpt,
                        commit_sha=commit_sha,
                    )
                    for item in group.members
                ]
            )
        await self.session.flush()

    async def get(
        self,
        analysis_id: UUID,
        *,
        language: str | None = None,
        path_prefix: str | None = None,
        limit: int = 100,
    ) -> QualityRecord | None:
        metadata = await self.session.scalar(
            select(AnalysisQualityMetadata).where(
                AnalysisQualityMetadata.analysis_job_id == analysis_id
            )
        )
        if metadata is None:
            return None
        filters = [UnusedCodeCandidateModel.analysis_job_id == analysis_id]
        member_filters = [DuplicateCodeMember.analysis_job_id == analysis_id]
        if language:
            filters.append(UnusedCodeCandidateModel.language == language)
            member_filters.append(DuplicateCodeMember.language == language)
        if path_prefix:
            filters.append(UnusedCodeCandidateModel.path.startswith(path_prefix))
            member_filters.append(DuplicateCodeMember.path.startswith(path_prefix))
        unused = tuple(
            (
                await self.session.scalars(
                    select(UnusedCodeCandidateModel)
                    .where(*filters)
                    .order_by(UnusedCodeCandidateModel.path, UnusedCodeCandidateModel.start_line)
                    .limit(limit)
                )
            ).all()
        )
        members = tuple(
            (
                await self.session.scalars(
                    select(DuplicateCodeMember)
                    .where(*member_filters)
                    .order_by(
                        DuplicateCodeMember.group_id,
                        DuplicateCodeMember.path,
                        DuplicateCodeMember.start_line,
                    )
                    .limit(limit)
                )
            ).all()
        )
        by_group: dict[str, list[DuplicateCodeMember]] = {}
        for member in members:
            by_group.setdefault(member.group_id, []).append(member)
        groups = tuple(
            (group, tuple(by_group[group.id]))
            for group in (
                await self.session.scalars(
                    select(DuplicateCodeGroup)
                    .where(
                        DuplicateCodeGroup.analysis_job_id == analysis_id,
                        DuplicateCodeGroup.id.in_(by_group),
                    )
                    .order_by(DuplicateCodeGroup.id)
                )
            ).all()
        )
        return QualityRecord(metadata, unused, groups)
