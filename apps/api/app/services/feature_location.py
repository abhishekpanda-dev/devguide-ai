import re
from collections import defaultdict, deque
from pathlib import PurePosixPath
from uuid import UUID

from app.models import RepositoryDependencyEdge, RepositoryFile, RepositoryFileIntelligence
from app.repositories import (
    AnalysisJobRepository,
    CodeFindingRepository,
    ParsedRepository,
    RepositoryQualityRepository,
    RepositoryRepository,
    RepositoryStructureRepository,
)
from app.schemas.feature_location import (
    ChangePlan,
    FeatureFile,
    FeatureFileRole,
    FeatureLocationResult,
    ImpactKind,
    ImpactSummary,
)
from app.services.finding import CodeFindingService

_INTENT = re.compile(
    r"\b(where\s+(?:is|are|should)|which\s+files?|what\s+(?:will|would|is)\s+(?:be\s+)?affected|"
    r"tests?\s+(?:cover|for|should)|trace\s+(?:the\s+)?(?:request|data|code)?\s*flow|"
    r"new\s+(?:developer|contributor)\s+start|start\s+as\s+a\s+new)\b",
    re.IGNORECASE,
)
_STOP = {
    "where",
    "is",
    "are",
    "should",
    "i",
    "modify",
    "implemented",
    "implementation",
    "which",
    "files",
    "file",
    "involved",
    "in",
    "what",
    "will",
    "would",
    "be",
    "affected",
    "if",
    "change",
    "tests",
    "test",
    "cover",
    "this",
    "feature",
    "trace",
    "the",
    "request",
    "data",
    "flow",
    "for",
    "a",
    "new",
    "developer",
    "contributor",
    "start",
    "as",
    "about",
    "module",
    "service",
}
_TOKEN = re.compile(r"[A-Za-z0-9_.-]+")


def is_feature_location_question(question: str) -> bool:
    return bool(_INTENT.search(question))


def extract_feature_phrase(question: str, *, maximum_tokens: int = 8) -> str:
    tokens = [token.lower().strip("._-") for token in _TOKEN.findall(question)]
    selected = [token for token in tokens if token and token not in _STOP][:maximum_tokens]
    return " ".join(selected)


def _role(file: RepositoryFile, info: RepositoryFileIntelligence) -> FeatureFileRole:
    path = file.path.lower()
    if file.is_test:
        return FeatureFileRole.TEST
    if file.is_configuration:
        return FeatureFileRole.CONFIGURATION
    if info.is_entry_point:
        return FeatureFileRole.ENTRY_POINT
    if re.search(r"(^|/)(api|routes?|endpoints?)(/|$)", path):
        return FeatureFileRole.API_ROUTE
    if re.search(r"(^|/)(components?|pages?|views?|frontend|web)(/|$)", path):
        return FeatureFileRole.UI
    if re.search(r"(^|/)(services?)(/|$)", path):
        return FeatureFileRole.SERVICE
    if re.search(r"(^|/)(repositories|dao|data)(/|$)", path):
        return FeatureFileRole.REPOSITORY
    if re.search(r"(^|/)(models?|schemas?)(/|$)", path):
        return FeatureFileRole.MODEL
    if re.search(r"(^|/)(workers?|jobs?|queue)(/|$)", path):
        return FeatureFileRole.WORKER
    return FeatureFileRole.UNKNOWN


class FeatureLocationService:
    def __init__(
        self,
        jobs: AnalysisJobRepository,
        parsed: ParsedRepository,
        structures: RepositoryStructureRepository,
        repositories: RepositoryRepository,
        findings: CodeFindingRepository,
        quality: RepositoryQualityRepository,
        *,
        maximum_files: int = 8,
        neighbor_depth: int = 2,
        related_tests_limit: int = 5,
    ) -> None:
        self.jobs, self.parsed, self.structures, self.repositories = (
            jobs,
            parsed,
            structures,
            repositories,
        )
        self.findings, self.quality = findings, quality
        self.maximum_files, self.neighbor_depth, self.related_tests_limit = (
            maximum_files,
            neighbor_depth,
            related_tests_limit,
        )

    async def retrieve(self, analysis_id: UUID, question: str) -> FeatureLocationResult | None:
        if not is_feature_location_question(question):
            return None
        phrase = extract_feature_phrase(question)
        record = await self.structures.get(analysis_id)
        if record is None:
            return None
        analysis = await self.jobs.get_by_id(analysis_id)
        repository = await self.repositories.get_by_id(analysis.repository_id) if analysis else None
        if record is None or repository is None:
            return None
        chunks = await self.parsed.list_chunks(analysis_id)
        chunk_text: dict[UUID, str] = defaultdict(str)
        for chunk in chunks:
            chunk_text[chunk.repository_file_id] += " " + chunk.content[:2000].lower()
        terms = tuple(dict.fromkeys(_TOKEN.findall((phrase or question).lower())))[:8]
        phrase_path = phrase.replace(" ", "_")
        rows = {file.id: (file, info) for file, info in record.files}
        scores: dict[UUID, float] = {}
        reasons: dict[UUID, list[str]] = defaultdict(list)
        for file_id, (file, info) in rows.items():
            path, name = file.path.lower(), file.file_name.lower()
            score = 0.0
            if phrase_path and phrase_path in path:
                score += 70
                reasons[file_id].append(f"Path matches the normalized feature phrase '{phrase}'.")
            for term in terms:
                if term == name.rsplit(".", 1)[0]:
                    score += 45
                    reasons[file_id].append(f"Exact filename match for '{term}'.")
                if term in PurePosixPath(path).parts:
                    score += 24
                    reasons[file_id].append(f"Path segment matches '{term}'.")
                elif term in path:
                    score += 12
                if term in chunk_text[file_id]:
                    score += 8
            if info.is_entry_point:
                score += 3
            score += min(info.inbound_dependency_count + info.outbound_dependency_count, 10) * 0.4
            if score > 4:
                scores[file_id] = score
        ordered_ids = sorted(scores, key=lambda key: (-scores[key], rows[key][0].path))
        if not ordered_ids:
            ordered_ids = [
                file_id
                for file_id, (_file, info) in sorted(
                    rows.items(),
                    key=lambda row: (
                        not row[1][1].is_entry_point,
                        -(row[1][1].inbound_dependency_count + row[1][1].outbound_dependency_count),
                        row[1][0].path,
                    ),
                )
                if info.is_entry_point
                or info.inbound_dependency_count + info.outbound_dependency_count > 0
            ]
            for file_id in ordered_ids:
                reasons[file_id].append(
                    "Probable entry point or highly connected starting file for contributor "
                    "orientation."
                )
        seed_ids = ordered_ids[: self.maximum_files]
        by_source: dict[UUID, list[RepositoryDependencyEdge]] = defaultdict(list)
        by_target: dict[UUID, list[RepositoryDependencyEdge]] = defaultdict(list)
        for edge in record.edges:
            by_source[edge.source_repository_file_id].append(edge)
            by_target[edge.target_repository_file_id].append(edge)
        direct_out = {
            edge.target_repository_file_id
            for file_id in seed_ids[:3]
            for edge in by_source[file_id]
        }
        direct_in = {
            edge.source_repository_file_id
            for file_id in seed_ids[:3]
            for edge in by_target[file_id]
        }
        visited = set(seed_ids) | direct_out | direct_in
        frontier = deque((item, 1) for item in sorted(direct_out | direct_in, key=str))
        indirect: set[UUID] = set()
        while frontier:
            current, depth = frontier.popleft()
            if depth >= self.neighbor_depth:
                continue
            neighbors = {e.target_repository_file_id for e in by_source[current]} | {
                e.source_repository_file_id for e in by_target[current]
            }
            for neighbor in sorted(neighbors, key=str):
                if neighbor not in visited:
                    visited.add(neighbor)
                    indirect.add(neighbor)
                    frontier.append((neighbor, depth + 1))
        commit = record.files[0][0].commit_sha if record.files else ""

        def item(
            file_id: UUID, kind: ImpactKind | None = None, reason: str | None = None
        ) -> FeatureFile:
            file, info = rows[file_id]
            confidence = min(0.95, 0.35 + scores.get(file_id, 10) / 100)
            return FeatureFile(
                repository_file_id=file.id,
                path=file.path,
                role=_role(file, info),
                confidence=confidence,
                reason=reason
                or "; ".join(dict.fromkeys(reasons[file_id]))
                or "Static dependency proximity to a likely feature file.",
                source_url=CodeFindingService.source_url(
                    repository.normalized_url, commit, file.path, 1, max(1, file.line_count)
                ),
                evidence=tuple(dict.fromkeys(reasons[file_id]))[:5],
                impact_kind=kind,
            )

        likely = tuple(item(file_id) for file_id in seed_ids)
        tests = []
        feature_stems = {PurePosixPath(rows[file_id][0].path).stem.lower() for file_id in seed_ids}
        for file_id, (file, _) in rows.items():
            if not file.is_test:
                continue
            lexical = any(
                term in file.path.lower() or term in chunk_text[file_id] for term in terms
            )
            convention = any(stem and stem in file.path.lower() for stem in feature_stems)
            linked = file_id in direct_in or file_id in direct_out
            if lexical or convention or linked:
                reason = (
                    "Likely related test by "
                    + ", ".join(
                        x
                        for x, ok in (
                            ("lexical reference", lexical),
                            ("filename convention", convention),
                            ("static dependency", linked),
                        )
                        if ok
                    )
                    + "; coverage is not proven."
                )
                tests.append(item(file_id, ImpactKind.INDIRECT, reason))
        tests = sorted(tests, key=lambda x: (-x.confidence, x.path))[: self.related_tests_limit]
        finding_page = await self.findings.list_for_analysis(analysis_id, limit=100)
        related_findings = tuple(
            f"{finding.path}: {finding.title}"
            for finding in (finding_page.findings if finding_page else ())
            if finding.repository_file_id in visited
        )[:10]
        quality = await self.quality.get(analysis_id, limit=100)
        quality_items = (
            []
            if quality is None
            else [
                f"{x.path}: {x.reason}" for x in quality.unused if x.repository_file_id in visited
            ]
        )
        entries = [
            file_id
            for file_id, (_, info) in rows.items()
            if info.is_entry_point and file_id in visited
        ]
        direct_dependencies = tuple(
            item(
                x,
                ImpactKind.DIRECT,
                "Direct persisted outgoing dependency from a likely feature file.",
            )
            for x in sorted(direct_out, key=lambda x: rows[x][0].path)[: self.maximum_files]
        )
        direct_dependents = tuple(
            item(
                x,
                ImpactKind.DIRECT,
                "Direct persisted incoming dependent of a likely feature file.",
            )
            for x in sorted(direct_in, key=lambda x: rows[x][0].path)[: self.maximum_files]
        )
        probable_indirect = tuple(
            item(x, ImpactKind.INDIRECT)
            for x in sorted(indirect, key=lambda x: rows[x][0].path)[: self.maximum_files]
        )
        limitations = (
            "Results are probable and based on bounded persisted static evidence.",
            "Static dependencies do not prove runtime behavior; dynamic wiring may be absent.",
            "Related tests are likely candidates to inspect, not proof of test coverage.",
        )
        paths = tuple(x.path for x in likely)
        affected = tuple(
            dict.fromkeys(
                x.path for x in (*direct_dependencies, *direct_dependents, *probable_indirect)
            )
        )
        return FeatureLocationResult(
            intent="change_impact"
            if re.search(r"affected|change|modify", question, re.I)
            else "feature_location",
            feature_phrase=phrase or "repository feature",
            likely_files=likely,
            impact_summary=ImpactSummary(
                direct_dependencies=direct_dependencies,
                direct_dependents=direct_dependents,
                probable_indirect=probable_indirect,
                probable_entry_points=tuple(
                    item(
                        x,
                        ImpactKind.INDIRECT,
                        "Probable entry point connected by persisted static evidence.",
                    )
                    for x in entries[: self.maximum_files]
                ),
                related_findings=related_findings,
                related_quality_candidates=tuple(quality_items[:10]),
                unknown_dynamic_impact=(
                    "Runtime registration, reflection, configuration, and external consumers "
                    "cannot be confirmed from static evidence."
                ),
            ),
            related_tests=tuple(tests),
            change_plan=ChangePlan(
                start_here=paths[:1],
                inspect_files=paths,
                likely_code_path=tuple(dict.fromkeys((*paths[:3], *affected[:3]))),
                potentially_affected_files=affected,
                tests_to_review=tuple(x.path for x in tests),
                risks_and_limitations=limitations,
            ),
            limitations=limitations,
        )
