from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import (
    AnalysisNotFoundError,
    AnalysisSummaryNotReadyError,
    PersistenceError,
)
from app.repositories import AnalysisJobRepository, ParsedRepository
from app.schemas import AnalysisLanguageSummary, AnalysisSummary


class AnalysisSummaryService:
    def __init__(
        self,
        jobs: AnalysisJobRepository,
        parsed: ParsedRepository,
    ) -> None:
        self._jobs = jobs
        self._parsed = parsed

    async def get_required(self, analysis_job_id: UUID) -> AnalysisSummary:
        try:
            analysis = await self._jobs.get_by_id(analysis_job_id)
            if analysis is None:
                raise AnalysisNotFoundError
            summary = await self._parsed.get_summary(analysis_job_id)
        except SQLAlchemyError as exc:
            raise PersistenceError from exc
        if summary is None:
            raise AnalysisSummaryNotReadyError
        return AnalysisSummary(
            analysis_job_id=analysis_job_id,
            files_analyzed=summary.files_analyzed,
            chunks_created=summary.chunks_created,
            languages=[
                AnalysisLanguageSummary(
                    language=item.language,
                    file_count=item.file_count,
                    line_count=item.line_count,
                )
                for item in summary.languages
            ],
            total_lines=summary.total_lines,
            test_file_count=summary.test_file_count,
            documentation_file_count=summary.documentation_file_count,
            skipped_file_count=summary.skipped_file_count,
            limitations=list(summary.limitations),
        )
