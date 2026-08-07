from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from app.ai.prompts.suggested_fix import SYSTEM_INSTRUCTIONS, build_suggested_fix_prompt
from app.ai.providers import ProviderSuggestedFixRequest, SuggestedFixProvider
from app.core.config import Settings
from app.core.exceptions import (
    AnalysisNotFoundError,
    CodeFindingsNotReadyError,
    GroundedAnswerValidationError,
    ResourceNotFoundError,
)
from app.findings.analyzer import redact_suspected_credentials
from app.models import AnalysisJobStatus
from app.repositories import (
    AnalysisJobRepository,
    CodeFindingRepository,
    ParsedRepository,
    RepositoryRepository,
)
from app.schemas.finding import SuggestedFixCitation, SuggestedFixResponse
from app.schemas.retrieval import MatchedChannel, RepositoryEvidence
from app.services.finding import CodeFindingService


class SuggestedFixService:
    def __init__(
        self,
        jobs: AnalysisJobRepository,
        repositories: RepositoryRepository,
        findings: CodeFindingRepository,
        parsed: ParsedRepository,
        provider: SuggestedFixProvider,
        settings: Settings,
    ) -> None:
        self.jobs, self.repositories, self.findings, self.parsed = (
            jobs,
            repositories,
            findings,
            parsed,
        )
        self.provider, self.settings = provider, settings

    async def generate(
        self, analysis_id: UUID, finding_id: UUID, correlation_id: str | None
    ) -> SuggestedFixResponse:
        analysis = await self.jobs.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError
        if analysis.status is not AnalysisJobStatus.COMPLETED:
            raise CodeFindingsNotReadyError
        finding = await self.findings.get_for_analysis(analysis_id, finding_id)
        if finding is None:
            raise ResourceNotFoundError("Code finding")
        repository = await self.repositories.get_by_id(analysis.repository_id)
        file, chunks = await self.parsed.context_for_file(analysis_id, finding.repository_file_id)
        if (
            repository is None
            or file is None
            or file.path != finding.path
            or file.commit_sha != finding.commit_sha
        ):
            raise GroundedAnswerValidationError
        path = PurePosixPath(file.path)
        if (
            path.is_absolute()
            or PureWindowsPath(file.path).is_absolute()
            or ".." in path.parts
            or finding.end_line > file.line_count
        ):
            raise GroundedAnswerValidationError
        relevant = [
            c
            for c in chunks
            if c.end_line >= finding.start_line - 12 and c.start_line <= finding.end_line + 12
        ]
        if not relevant:
            raise ResourceNotFoundError("Sufficient finding evidence")
        excerpt = redact_suspected_credentials("\n".join(c.content for c in relevant))[
            : self.settings.ai_maximum_evidence_characters
        ]
        if not excerpt.strip():
            raise ResourceNotFoundError("Sufficient finding evidence")
        start, end = min(c.start_line for c in relevant), max(c.end_line for c in relevant)
        evidence_id = f"finding:{finding.id}"
        evidence = RepositoryEvidence(
            repository_file_id=file.id,
            chunk_id=evidence_id,
            path=file.path,
            language=file.language,
            start_line=start,
            end_line=end,
            excerpt=excerpt,
            score=100,
            matched_channels=(MatchedChannel.EXACT_PATH,),
            content_hash=file.content_hash,
            commit_sha=file.commit_sha,
        )
        result = await self.provider.generate_suggested_fix(
            ProviderSuggestedFixRequest(
                evidence_id=evidence_id,
                rule_id=finding.rule_id,
                finding_explanation=finding.explanation,
                deterministic_recommendation=finding.deterministic_recommendation,
                evidence=evidence,
                system_instructions=SYSTEM_INSTRUCTIONS,
                user_prompt=build_suggested_fix_prompt(
                    rule_id=finding.rule_id,
                    explanation=finding.explanation,
                    recommendation=finding.deterministic_recommendation,
                    evidence=evidence,
                ),
                output_schema=self._schema(),
                correlation_id=correlation_id,
                maximum_output_tokens=self.settings.ai_maximum_output_tokens,
                temperature=self.settings.ai_temperature,
            )
        )
        if (
            result.cited_evidence_ids != (evidence_id,)
            or not result.explanation.strip()
            or not result.probable_fix.strip()
        ):
            raise GroundedAnswerValidationError
        citation = SuggestedFixCitation(
            path=file.path,
            start_line=start,
            end_line=end,
            content_hash=file.content_hash,
            source_url=CodeFindingService.source_url(
                repository.normalized_url, file.commit_sha, file.path, start, end
            ),
        )
        return SuggestedFixResponse(
            analysis_job_id=analysis_id,
            finding_id=finding_id,
            rule_id=finding.rule_id,
            explanation=result.explanation,
            probable_fix=result.probable_fix,
            example_code=result.example_code,
            citations=[citation],
            provider=result.provider_name,
            model=result.model_name,
            limitations=list(result.limitations),
            correlation_id=correlation_id,
        )

    @staticmethod
    def _schema() -> dict[str, object]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "explanation",
                "probable_fix",
                "example_code",
                "cited_evidence_ids",
                "limitations",
            ],
            "properties": {
                "explanation": {"type": "string"},
                "probable_fix": {"type": "string"},
                "example_code": {"type": ["string", "null"]},
                "cited_evidence_ids": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
            },
        }
