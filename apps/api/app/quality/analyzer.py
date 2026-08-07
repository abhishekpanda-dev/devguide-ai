import ast
import hashlib
import io
import re
import tokenize
from collections import Counter, defaultdict

from app.findings import FindingsAnalysisResult
from app.models import FindingSeverity
from app.parser import RepositoryParseResult
from app.quality.types import (
    DuplicateGroupCandidate,
    DuplicateMemberCandidate,
    QualityAnalysisResult,
    ScoreDeduction,
    UnusedCodeCandidate,
)
from app.structure import StructureAnalysisResult

_MAGIC = {"main", "setup", "teardown", "startup", "shutdown", "handler", "get", "post"}
_EXCLUDED_PATH = re.compile(r"(^|/)(vendor|vendors|node_modules|dist|build|coverage)(/|$)")


class RepositoryQualityAnalyzer:
    def __init__(
        self,
        *,
        maximum_unused: int = 100,
        maximum_duplicate_groups: int = 50,
        maximum_duplicate_members: int = 8,
        minimum_duplicate_lines: int = 5,
        minimum_duplicate_tokens: int = 20,
    ) -> None:
        self.maximum_unused = maximum_unused
        self.maximum_duplicate_groups = maximum_duplicate_groups
        self.maximum_duplicate_members = maximum_duplicate_members
        self.minimum_duplicate_lines = minimum_duplicate_lines
        self.minimum_duplicate_tokens = minimum_duplicate_tokens

    def analyze(
        self,
        parsed: RepositoryParseResult,
        findings: FindingsAnalysisResult,
        structure: StructureAnalysisResult,
    ) -> QualityAnalysisResult:
        eligible = [
            item
            for item in parsed.files
            if self._eligible(item.metadata.path, item.metadata.is_test, item.metadata.is_generated)
        ]
        names = Counter(
            match.group(0)
            for item in eligible
            for match in re.finditer(r"\b[A-Za-z_]\w*\b", item.content)
        )
        entries = {item.path for item in structure.entry_points}
        unused: list[UnusedCodeCandidate] = []
        blocks: list[tuple[str, DuplicateMemberCandidate]] = []
        limitations = [
            "Unused-code results are high-confidence static candidates; "
            "dynamic references may not be visible.",
            "Duplicate detection reports exact normalized Python top-level blocks only.",
        ]
        for item in eligible:
            if item.metadata.language != "python":
                continue
            try:
                tree = ast.parse(item.content, filename=item.metadata.path)
            except (SyntaxError, ValueError):
                limitations.append(f"Python syntax could not be analyzed for {item.metadata.path}.")
                continue
            lines = item.content.splitlines()
            for node in tree.body:
                if not isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ) or not hasattr(node, "end_lineno"):
                    continue
                start, end = node.lineno, node.end_lineno or node.lineno
                excerpt = "\n".join(lines[start - 1 : end])[:1200]
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                if (
                    item.metadata.path not in entries
                    and node.name not in _MAGIC
                    and not node.name.startswith("__")
                    and names[node.name] == 1
                ):
                    unused.append(
                        UnusedCodeCandidate(
                            node.name,
                            kind,
                            item.metadata.path,
                            "python",
                            start,
                            end,
                            f"Top-level {kind} has no other lexical reference in persisted "
                            "eligible source and its file is not a probable entry point.",
                            0.9,
                            "Review dynamic/framework usage, then remove or document this "
                            "candidate if it is genuinely unused.",
                            excerpt,
                        )
                    )
                normalized, tokens = self._normalize_python(excerpt)
                if (
                    end - start + 1 >= self.minimum_duplicate_lines
                    and tokens >= self.minimum_duplicate_tokens
                ):
                    fingerprint = hashlib.sha256(normalized.encode()).hexdigest()
                    blocks.append(
                        (
                            fingerprint,
                            DuplicateMemberCandidate(
                                item.metadata.path, "python", start, end, excerpt
                            ),
                        )
                    )
        unused = sorted(unused, key=lambda x: (x.path, x.start_line, x.symbol_name))[
            : self.maximum_unused
        ]
        buckets: dict[str, list[DuplicateMemberCandidate]] = defaultdict(list)
        for fingerprint, member in blocks:
            buckets[fingerprint].append(member)
        groups = []
        for fingerprint, members in sorted(buckets.items()):
            distinct = sorted(
                {(m.path, m.start_line, m.end_line): m for m in members}.values(),
                key=lambda m: (m.path, m.start_line),
            )
            if len(distinct) < 2:
                continue
            groups.append(
                DuplicateGroupCandidate(
                    f"dup-{fingerprint[:16]}",
                    fingerprint,
                    tuple(distinct[: self.maximum_duplicate_members]),
                    1.0,
                    "Review whether the repeated block should be extracted into a shared, "
                    "well-named implementation.",
                )
            )
        groups = groups[: self.maximum_duplicate_groups]
        deductions = self._deductions(findings, len(unused), len(groups), structure)
        category_scores = {
            name: max(0, 100 - sum(d.points_deducted for d in deductions if d.category == name))
            for name in ("maintainability", "reliability", "security", "structure")
        }
        overall = round(sum(category_scores.values()) / len(category_scores))
        return QualityAnalysisResult(
            overall,
            category_scores,
            deductions,
            tuple(unused),
            tuple(groups),
            tuple(dict.fromkeys(limitations)),
        )

    @staticmethod
    def _eligible(path: str, is_test: bool, is_generated: bool) -> bool:
        lower = path.lower()
        return (
            not is_test
            and not is_generated
            and not _EXCLUDED_PATH.search(lower)
            and not lower.endswith((".min.js", ".lock", "lock.json"))
        )

    @staticmethod
    def _normalize_python(content: str) -> tuple[str, int]:
        kept = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(content).readline):
                if token.type not in {
                    tokenize.COMMENT,
                    tokenize.NL,
                    tokenize.NEWLINE,
                    tokenize.INDENT,
                    tokenize.DEDENT,
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                }:
                    kept.append(token.string)
        except (tokenize.TokenError, IndentationError):
            return "", 0
        return " ".join(kept), len(kept)

    @staticmethod
    def _deductions(
        findings: FindingsAnalysisResult,
        unused: int,
        duplicates: int,
        structure: StructureAnalysisResult,
    ) -> tuple[ScoreDeduction, ...]:
        counts = Counter(item.severity for item in findings.findings)
        result = []
        policies = (
            (FindingSeverity.HIGH, "security", 8, 32),
            (FindingSeverity.WARNING, "reliability", 3, 24),
            (FindingSeverity.INFO, "maintainability", 1, 12),
        )
        for severity, category, each, cap in policies:
            count = counts[severity]
            if count:
                points = min(cap, count * each)
                result.append(
                    ScoreDeduction(
                        category,
                        f"{severity.value}_findings",
                        count,
                        points,
                        f"Capped deterministic penalty for {severity.value} static findings.",
                    )
                )
        if duplicates:
            result.append(
                ScoreDeduction(
                    "maintainability",
                    "duplicate_groups",
                    duplicates,
                    min(15, duplicates * 2),
                    "Exact normalized duplicate groups increase maintenance effort.",
                )
            )
        if unused:
            result.append(
                ScoreDeduction(
                    "maintainability",
                    "unused_candidates",
                    unused,
                    min(10, unused),
                    "High-confidence unused-code candidates increase review burden.",
                )
            )
        outbound = Counter(edge.source_path for edge in structure.edges)
        fanout = sum(1 for count in outbound.values() if count >= 10)
        if fanout:
            result.append(
                ScoreDeduction(
                    "structure",
                    "high_fan_out_files",
                    fanout,
                    min(20, fanout * 4),
                    "Files with at least ten resolved outbound dependencies are static "
                    "coupling signals.",
                )
            )
        return tuple(result)
