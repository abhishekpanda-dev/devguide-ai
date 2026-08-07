from dataclasses import dataclass

from app.models import FindingCategory, FindingSeverity


@dataclass(frozen=True, slots=True)
class FindingCandidate:
    rule_id: str
    severity: FindingSeverity
    category: FindingCategory
    title: str
    explanation: str
    path: str
    start_line: int
    end_line: int
    evidence_excerpt: str
    deterministic_recommendation: str
    confidence: float
    content_hash: str
    commit_sha: str


@dataclass(frozen=True, slots=True)
class FindingsAnalysisResult:
    findings: tuple[FindingCandidate, ...]
    limitations: tuple[str, ...] = ()
