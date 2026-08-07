from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnusedCodeCandidate:
    symbol_name: str
    symbol_kind: str
    path: str
    language: str
    start_line: int
    end_line: int
    reason: str
    confidence: float
    recommendation: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class DuplicateMemberCandidate:
    path: str
    language: str
    start_line: int
    end_line: int
    excerpt: str


@dataclass(frozen=True, slots=True)
class DuplicateGroupCandidate:
    group_id: str
    fingerprint: str
    members: tuple[DuplicateMemberCandidate, ...]
    confidence: float
    recommendation: str


@dataclass(frozen=True, slots=True)
class ScoreDeduction:
    category: str
    signal_type: str
    count: int
    points_deducted: int
    explanation: str


@dataclass(frozen=True, slots=True)
class QualityAnalysisResult:
    overall_score: int
    category_scores: dict[str, int]
    deductions: tuple[ScoreDeduction, ...]
    unused_candidates: tuple[UnusedCodeCandidate, ...]
    duplicate_groups: tuple[DuplicateGroupCandidate, ...]
    limitations: tuple[str, ...]
    score_version: str = "quality-v1"
