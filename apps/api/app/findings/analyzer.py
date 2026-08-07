import ast
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from app.findings.types import FindingCandidate, FindingsAnalysisResult
from app.models import FindingCategory as C
from app.models import FindingSeverity as S
from app.parser import RepositoryParseResult
from app.parser.classification import (
    EXCLUDED_FINDINGS_CLASSIFICATIONS,
    FileClassification,
    classify_file,
)
from app.parser.types import SourceFile


@dataclass(frozen=True, slots=True)
class Rule:
    severity: S
    category: C
    title: str
    explanation: str
    recommendation: str
    confidence: float


RULES = {
    "maintainability.todo": Rule(
        S.INFO,
        C.MAINTAINABILITY,
        "TODO maintenance marker",
        "A TODO marker identifies work that may need completion or review.",
        "Review and track actionable work, then remove the marker when complete.",
        0.95,
    ),
    "maintainability.fixme": Rule(
        S.WARNING,
        C.MAINTAINABILITY,
        "FIXME maintenance marker",
        "A FIXME marker identifies known behavior that warrants review.",
        "Review the behavior and replace the marker with a tracked, tested correction.",
        0.95,
    ),
    "maintainability.hack": Rule(
        S.WARNING,
        C.MAINTAINABILITY,
        "HACK maintenance marker",
        "A HACK marker identifies a potentially fragile workaround.",
        "Document the workaround and replace it with a supported approach when practical.",
        0.95,
    ),
    "maintainability.large-file": Rule(
        S.INFO,
        C.MAINTAINABILITY,
        "Very large source file",
        "Large files can be harder to understand, review, and test.",
        "Review whether cohesive responsibilities can be separated without changing behavior.",
        1,
    ),
    "python.eval": Rule(
        S.HIGH,
        C.SECURITY,
        "Potential eval() execution",
        "eval() interprets a string as Python code and can be dangerous with untrusted data.",
        "Prefer explicit parsing or a constrained data format.",
        0.99,
    ),
    "python.exec": Rule(
        S.HIGH,
        C.SECURITY,
        "Potential exec() execution",
        "exec() executes dynamic Python code and expands untrusted-input impact.",
        "Use explicit functions, dispatch tables, or constrained parsing.",
        0.99,
    ),
    "python.broad-exception": Rule(
        S.WARNING,
        C.RELIABILITY,
        "Broad exception handling",
        "Catching Exception or BaseException can conceal unrelated failures.",
        "Catch only the narrow exception types the operation can handle.",
        0.98,
    ),
    "python.empty-exception": Rule(
        S.WARNING,
        C.RELIABILITY,
        "Empty exception handler",
        "An exception handler containing only pass silently discards a failure.",
        "Handle the failure explicitly or document why it can safely be ignored.",
        0.99,
    ),
    "python.subprocess-shell": Rule(
        S.HIGH,
        C.SECURITY,
        "Subprocess uses shell=True",
        "Passing commands through a shell can enable command injection.",
        "Pass an argument list without shell=True and validate influenced values.",
        0.99,
    ),
    "security.hardcoded-credential": Rule(
        S.HIGH,
        C.SECURITY,
        "Possible hardcoded credential",
        "A credential-like variable is assigned a literal source value.",
        "Load it from an environment variable or secret manager and rotate it if real.",
        0.9,
    ),
    "security.debug-enabled": Rule(
        S.WARNING,
        C.SECURITY,
        "Debug mode explicitly enabled",
        "Debug mode can expose internal details when deployed.",
        "Disable debug by default and enable it only through local configuration.",
        0.95,
    ),
    "network.missing-timeout": Rule(
        S.WARNING,
        C.RELIABILITY,
        "Network request without explicit timeout",
        "A recognized HTTP call has no explicit timeout.",
        "Set a bounded timeout and handle timeout failures.",
        0.9,
    ),
    "python.mutable-default-argument": Rule(
        S.WARNING,
        C.RELIABILITY,
        "Mutable default argument",
        "A mutable default value is shared across calls and can retain unexpected state.",
        "Use None as the default and create the mutable value inside the function.",
        0.99,
    ),
    "python.bare-except": Rule(
        S.WARNING,
        C.RELIABILITY,
        "Bare exception handler",
        "A bare except handler catches system-exiting exceptions as well as application errors.",
        "Catch the narrow exception types that the operation can handle.",
        0.99,
    ),
    "python.runtime-assert": Rule(
        S.INFO,
        C.RELIABILITY,
        "Assert used for runtime validation",
        "Assertions can be disabled and should not enforce required runtime input validation.",
        "Use an explicit conditional and raise an appropriate exception.",
        0.95,
    ),
    "security.tls-verification-disabled": Rule(
        S.HIGH,
        C.SECURITY,
        "TLS certificate verification disabled",
        "A recognized HTTP call explicitly disables TLS certificate verification.",
        "Enable certificate verification and configure a trusted CA bundle when needed.",
        0.99,
    ),
}
MARKER = re.compile(r"\b(TODO|FIXME|HACK)\b", re.I)
CREDENTIAL = re.compile(
    r"(?i)\b(?:api_?key|access_?token|auth_?token|client_?secret|password|secret)\b\s*(?::[^=]{0,100})?=\s*([\"'])([^\"'\r\n]{4,512})\1"
)
SAFE = {"changeme", "example", "placeholder", "redacted", "test", "your-key-here"}


def redact_suspected_credentials(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        whole = match.group(0)
        start = match.start(2) - match.start(0)
        end = match.end(2) - match.start(0)
        return whole[:start] + "[REDACTED]" + whole[end:]

    return CREDENTIAL.sub(replace, value)


class DeterministicFindingsAnalyzer:
    def __init__(self, *, large_file_line_threshold: int, maximum_findings: int) -> None:
        if min(large_file_line_threshold, maximum_findings) < 1:
            raise ValueError("bounds must be positive")
        self.threshold = large_file_line_threshold
        self.maximum = maximum_findings

    def analyze(self, result: RepositoryParseResult, *, commit_sha: str) -> FindingsAnalysisResult:
        found = []
        limitations = []
        for source in result.files:
            if not self.safe_path(source.metadata.path):
                raise ValueError("unsafe findings path")
            classification = self.classification(source)
            if classification in EXCLUDED_FINDINGS_CLASSIFICATIONS:
                continue
            if classification in {
                FileClassification.SOURCE,
                FileClassification.TEST,
                FileClassification.CONFIGURATION,
                FileClassification.DOCUMENTATION,
                FileClassification.UNKNOWN,
            }:
                found.extend(self.text_rules(source, commit_sha, classification))
            if source.metadata.language == "python" and classification in {
                FileClassification.SOURCE,
                FileClassification.TEST,
            }:
                try:
                    found.extend(self.python_rules(source, commit_sha, classification))
                except (SyntaxError, ValueError):
                    limitations.append(
                        f"{source.metadata.path}: Python syntax could not be inspected."
                    )
            if (
                source.metadata.line_count >= self.threshold
                and classification is FileClassification.SOURCE
            ):
                found.append(
                    self.make(
                        "maintainability.large-file",
                        source,
                        commit_sha,
                        1,
                        max(1, source.metadata.line_count),
                        f"Source file contains {source.metadata.line_count} lines.",
                    )
                )
        unique = {
            (x.path, x.rule_id, x.start_line, x.end_line, " ".join(x.evidence_excerpt.split())): x
            for x in found
        }
        found = sorted(unique.values(), key=lambda x: (x.path, x.start_line, x.end_line, x.rule_id))
        if len(found) > self.maximum:
            found = found[: self.maximum]
            limitations.append("The configured maximum findings count was reached.")
        return FindingsAnalysisResult(tuple(found), tuple(sorted(set(limitations))))

    def text_rules(
        self, source: SourceFile, sha: str, classification: FileClassification
    ) -> list[FindingCandidate]:
        out = []
        for number, line in enumerate(source.content.splitlines(), 1):
            line = line[:4096]
            for marker in sorted({m.group(1).lower() for m in MARKER.finditer(line)}):
                out.append(
                    self.make(
                        f"maintainability.{marker}", source, sha, number, number, self.excerpt(line)
                    )
                )
            match = (
                CREDENTIAL.search(line)
                if classification in {FileClassification.SOURCE, FileClassification.CONFIGURATION}
                else None
            )
            if match and self.suspicious(match.group(2)):
                redacted = redact_suspected_credentials(line)
                out.append(
                    self.make(
                        "security.hardcoded-credential",
                        source,
                        sha,
                        number,
                        number,
                        self.excerpt(redacted),
                    )
                )
        return out

    def python_rules(
        self, source: SourceFile, sha: str, classification: FileClassification
    ) -> list[FindingCandidate]:
        tree = ast.parse(source.content)
        lines = source.content.splitlines()
        out = []
        for node in ast.walk(tree):
            rule = None
            if isinstance(node, ast.Call):
                name = self.name(node.func)
                if name in {"eval", "exec"}:
                    rule = f"python.{name}"
                elif (
                    name.startswith("subprocess.")
                    and name.rsplit(".", 1)[-1]
                    in {"run", "Popen", "call", "check_call", "check_output"}
                    and self.true_kw(node, "shell")
                ):
                    rule = "python.subprocess-shell"
                elif self.network(name) and not any(k.arg == "timeout" for k in node.keywords):
                    rule = "network.missing-timeout"
                if self.network(name) and self.false_kw(node, "verify"):
                    rule = "security.tls-verification-disabled"
                elif name.endswith(".run") and self.true_kw(node, "debug"):
                    rule = "security.debug-enabled"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if (
                    isinstance(node.value, ast.Constant)
                    and node.value.value is True
                    and any(self.debug_target(t) for t in targets)
                ):
                    rule = "security.debug-enabled"
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    out.append(self.node("python.bare-except", node, source, sha, lines))
                elif self.broad(node.type):
                    out.append(self.node("python.broad-exception", node, source, sha, lines))
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    rule = "python.empty-exception"
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defaults = (
                    *node.args.defaults,
                    *(x for x in node.args.kw_defaults if x is not None),
                )
                mutable = next(
                    (x for x in defaults if isinstance(x, (ast.List, ast.Dict, ast.Set))), None
                )
                if mutable is not None:
                    out.append(
                        self.node("python.mutable-default-argument", mutable, source, sha, lines)
                    )
            elif isinstance(node, ast.Assert) and classification is FileClassification.SOURCE:
                rule = "python.runtime-assert"
            if rule:
                out.append(self.node(rule, node, source, sha, lines))
        return out

    def node(
        self, rule: str, node: ast.AST, source: SourceFile, sha: str, lines: list[str]
    ) -> FindingCandidate:
        start = max(1, getattr(node, "lineno", 1))
        end = max(start, getattr(node, "end_lineno", start))
        return self.make(
            rule,
            source,
            sha,
            start,
            end,
            self.excerpt("\n".join(lines[start - 1 : min(end, start + 2)])),
        )

    @staticmethod
    def name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = DeterministicFindingsAnalyzer.name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return ""

    @staticmethod
    def true_kw(node: ast.Call, name: str) -> bool:
        return any(
            k.arg == name and isinstance(k.value, ast.Constant) and k.value.value is True
            for k in node.keywords
        )

    @staticmethod
    def false_kw(node: ast.Call, name: str) -> bool:
        return any(
            k.arg == name and isinstance(k.value, ast.Constant) and k.value.value is False
            for k in node.keywords
        )

    @staticmethod
    def network(name: str) -> bool:
        parts = name.split(".")
        return (
            len(parts) > 1
            and parts[0] in {"requests", "httpx"}
            and parts[-1] in {"get", "post", "put", "patch", "delete", "head", "request"}
        )

    @staticmethod
    def debug_target(node: ast.expr) -> bool:
        return DeterministicFindingsAnalyzer.name(node).lower().rsplit(".", 1)[-1] in {
            "debug",
            "debug_mode",
        }

    @staticmethod
    def broad(node: ast.expr | None) -> bool:
        return (isinstance(node, ast.Name) and node.id in {"Exception", "BaseException"}) or (
            isinstance(node, ast.Tuple)
            and any(DeterministicFindingsAnalyzer.broad(x) for x in node.elts)
        )

    @staticmethod
    def suspicious(value: str) -> bool:
        value = value.strip().lower()
        return (
            value not in SAFE
            and "example" not in value
            and "placeholder" not in value
            and not value.startswith("${")
        )

    @staticmethod
    def safe_path(value: str) -> bool:
        path = PurePosixPath(value)
        return (
            bool(value)
            and "\\" not in value
            and not path.is_absolute()
            and not PureWindowsPath(value).is_absolute()
            and ".." not in path.parts
        )

    @staticmethod
    def classification(source: SourceFile) -> FileClassification:
        return classify_file(
            source.metadata.path,
            language=source.metadata.language,
            is_test=source.metadata.is_test,
            is_documentation=source.metadata.is_documentation,
            is_configuration=source.metadata.is_configuration,
            content_prefix=source.content,
        )

    @staticmethod
    def excerpt(value: str) -> str:
        return value.strip()[:500]

    @staticmethod
    def make(
        rule_id: str, source: SourceFile, sha: str, start: int, end: int, evidence: str
    ) -> FindingCandidate:
        r = RULES[rule_id]
        return FindingCandidate(
            rule_id,
            r.severity,
            r.category,
            r.title,
            r.explanation,
            source.metadata.path,
            start,
            end,
            evidence,
            r.recommendation,
            r.confidence,
            source.metadata.content_hash,
            sha,
        )
