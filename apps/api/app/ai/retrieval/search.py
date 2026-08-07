import re
from dataclasses import dataclass

from app.ai.validators.citations import CitationValidator
from app.repositories.parsed import ParsedRepository, SearchCandidate
from app.schemas.retrieval import (
    MatchedChannel,
    RepositoryEvidence,
    SearchCoverage,
    SearchRepositoryRequest,
    SearchRepositoryResult,
)

# Deterministic lexical ranking v1. The maximum score is 110.
EXACT_PATH_WEIGHT = 40.0
PARTIAL_PATH_WEIGHT = 20.0
EXACT_PHRASE_WEIGHT = 25.0
TOKEN_OVERLAP_WEIGHT = 20.0
SYMBOL_WEIGHT = 15.0
LANGUAGE_FILTER_WEIGHT = 5.0
PATH_PREFIX_WEIGHT = 5.0

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
_SYMBOL_DECLARATION = re.compile(
    r"(?im)^\s*(?:class|def|async\s+def|function)\s+([A-Za-z_][A-Za-z0-9_]*)\b"
)
_CONFIG_KEY = re.compile(r"(?m)^\s*[\"']?([A-Za-z_][A-Za-z0-9_.-]*)[\"']?\s*[:=]")


@dataclass(frozen=True, slots=True)
class _RankedCandidate:
    candidate: SearchCandidate
    score: float
    channels: tuple[MatchedChannel, ...]


class SearchRepositoryService:
    def __init__(
        self, repository: ParsedRepository, validator: CitationValidator | None = None
    ) -> None:
        self._repository = repository
        self._validator = validator or CitationValidator()

    async def search(self, request: SearchRepositoryRequest) -> SearchRepositoryResult:
        candidates = await self._repository.search_candidates(
            request.analysis_job_id,
            languages=request.languages,
            path_prefix=request.path_prefix,
        )
        valid = [item for item in candidates if not self._validator.validate(item)]
        ranked = [self._rank(item, request) for item in valid]
        strong = [item for item in ranked if item.score >= request.minimum_score]
        strong.sort(key=self._sort_key)
        deduplicated = self._deduplicate(strong)
        selected = deduplicated[: request.limit]
        evidence = tuple(self._to_evidence(item) for item in selected)
        attempted = [
            MatchedChannel.EXACT_PATH,
            MatchedChannel.PARTIAL_PATH,
            MatchedChannel.EXACT_PHRASE,
            MatchedChannel.TOKEN_OVERLAP,
            MatchedChannel.SYMBOL,
        ]
        if request.languages:
            attempted.append(MatchedChannel.LANGUAGE)
        if request.path_prefix:
            attempted.append(MatchedChannel.PATH_PREFIX)
        limitations: tuple[str, ...] = ()
        if not evidence:
            limitations = (
                "Insufficient persisted lexical evidence met the minimum score.",
                "Semantic embeddings and AI answer generation are not implemented.",
            )
        return SearchRepositoryResult(
            analysis_job_id=request.analysis_job_id,
            query=request.query,
            evidence=evidence,
            total_candidates=len(candidates),
            returned_count=len(evidence),
            coverage=SearchCoverage(
                channels=tuple(attempted),
                candidate_files=len({item.repository_file_id for item in candidates}),
                candidate_chunks=len(candidates),
                strong_matches=len(strong),
            ),
            limitations=limitations,
        )

    @staticmethod
    def _rank(candidate: SearchCandidate, request: SearchRepositoryRequest) -> _RankedCandidate:
        query = request.query.casefold()
        path = candidate.path.casefold()
        content = candidate.content.casefold()
        query_tokens = {item.casefold() for item in _TOKEN.findall(request.query)}
        content_tokens = {item.casefold() for item in _TOKEN.findall(candidate.content)}
        channels: list[MatchedChannel] = []
        score = 0.0
        if query == path:
            score += EXACT_PATH_WEIGHT
            channels.append(MatchedChannel.EXACT_PATH)
        elif query in path or path in query:
            score += PARTIAL_PATH_WEIGHT
            channels.append(MatchedChannel.PARTIAL_PATH)
        if query in content:
            score += EXACT_PHRASE_WEIGHT
            channels.append(MatchedChannel.EXACT_PHRASE)
        overlap = query_tokens & content_tokens
        if query_tokens and overlap:
            score += TOKEN_OVERLAP_WEIGHT * len(overlap) / len(query_tokens)
            channels.append(MatchedChannel.TOKEN_OVERLAP)
        symbols = {
            match.casefold()
            for pattern in (_SYMBOL_DECLARATION, _CONFIG_KEY)
            for match in pattern.findall(candidate.content)
        }
        if query_tokens & symbols:
            score += SYMBOL_WEIGHT
            channels.append(MatchedChannel.SYMBOL)
        if request.languages:
            score += LANGUAGE_FILTER_WEIGHT
            channels.append(MatchedChannel.LANGUAGE)
        if request.path_prefix:
            score += PATH_PREFIX_WEIGHT
            channels.append(MatchedChannel.PATH_PREFIX)
        return _RankedCandidate(candidate, round(score, 6), tuple(channels))

    @staticmethod
    def _sort_key(item: _RankedCandidate) -> tuple[float, str, int, int, str]:
        candidate = item.candidate
        return (
            -item.score,
            candidate.path,
            candidate.start_line,
            candidate.end_line,
            candidate.chunk_id,
        )

    @staticmethod
    def _deduplicate(items: list[_RankedCandidate]) -> list[_RankedCandidate]:
        kept: list[_RankedCandidate] = []
        hashes: set[str] = set()
        ranges: dict[object, list[tuple[int, int]]] = {}
        for item in items:
            candidate = item.candidate
            if candidate.content_hash in hashes:
                continue
            file_ranges = ranges.setdefault(candidate.repository_file_id, [])
            if any(
                candidate.start_line <= end and start <= candidate.end_line
                for start, end in file_ranges
            ):
                continue
            hashes.add(candidate.content_hash)
            file_ranges.append((candidate.start_line, candidate.end_line))
            kept.append(item)
        return kept

    @staticmethod
    def _to_evidence(item: _RankedCandidate) -> RepositoryEvidence:
        candidate = item.candidate
        return RepositoryEvidence(
            repository_file_id=candidate.repository_file_id,
            chunk_id=candidate.chunk_id,
            path=candidate.path,
            language=candidate.language,
            start_line=candidate.start_line,
            end_line=candidate.end_line,
            excerpt=candidate.content,
            score=item.score,
            matched_channels=item.channels,
            content_hash=candidate.content_hash,
            commit_sha=candidate.commit_sha,
            limitations=candidate.limitations,
        )


class SearchRepositorySkill:
    """Internal runtime adapter for the documented Search Repository skill."""

    def __init__(self, repository: ParsedRepository) -> None:
        self._service = SearchRepositoryService(repository)

    async def search(self, request: SearchRepositoryRequest) -> SearchRepositoryResult:
        return await self._service.search(request)
