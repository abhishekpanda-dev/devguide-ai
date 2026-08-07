import ast
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from app.findings.types import FindingCandidate, FindingsAnalysisResult
from app.models import FindingCategory as C
from app.models import FindingSeverity as S
from app.parser import RepositoryParseResult
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
        1,
    ),
    "maintainability.fixme": Rule(
        S.WARNING,
        C.MAINTAINABILITY,
        "FIXME maintenance marker",
        "A FIXME marker identifies known behavior that warrants review.",
        "Review the behavior and replace the marker with a tracked, tested correction.",
        1,
    ),
    "maintainability.hack": Rule(
        S.WARNING,
        C.MAINTAINABILITY,
        "HACK maintenance marker",
        "A HACK marker identifies a potentially fragile workaround.",
        "Document the workaround and replace it with a supported approach when practical.",
        1,
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
}
MARKER = re.compile(r"\b(TODO|FIXME|HACK)\b", re.I)
CREDENTIAL = re.compile(
    r"(?i)\b(?:api_?key|access_?token|auth_?token|client_?secret|password|secret)\b\s*(?::[^=]{0,100})?=\s*([\"'])([^\"'\r\n]{4,512})\1"
)
SAFE = {"changeme", "example", "placeholder", "redacted", "test", "your-key-here"}
LARGE_FILE_EXCLUDED_NAMES = {
    "cargo.lock",
    "composer.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "yarn.lock",
}
LARGE_FILE_EXCLUDED_DIRECTORIES = {"build", "dist", "node_modules", "vendor"}
LARGE_FILE_GENERATED_SUFFIXES = (".min.css", ".min.js", ".map")


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
            found.extend(self.text_rules(source, commit_sha))
            if source.metadata.language == "python":
                try:
                    found.extend(self.python_rules(source, commit_sha))
                except (SyntaxError, ValueError):
                    limitations.append(
                        f"{source.metadata.path}: Python syntax could not be inspected."
                    )
            if source.metadata.line_count >= self.threshold and self.large_file_eligible(source):
                found.append(
                    self.make(
                        "maintainability.large-file",
                        source,
                        commit_sha,
                        1,
                        max(1, source.metadata.line_count),
                        f"File contains {source.metadata.line_count} lines.",
                    )
                )
        found.sort(key=lambda x: (x.path, x.start_line, x.end_line, x.rule_id))
        if len(found) > self.maximum:
            found = found[: self.maximum]
            limitations.append("The configured maximum findings count was reached.")
        return FindingsAnalysisResult(tuple(found), tuple(sorted(set(limitations))))

    def text_rules(self, source: SourceFile, sha: str) -> list[FindingCandidate]:
        out = []
        for number, line in enumerate(source.content.splitlines(), 1):
            line = line[:4096]
            for marker in sorted({m.group(1).lower() for m in MARKER.finditer(line)}):
                out.append(
                    self.make(
                        f"maintainability.{marker}", source, sha, number, number, self.excerpt(line)
                    )
                )
            match = CREDENTIAL.search(line)
            if match and self.suspicious(match.group(2)):
                redacted = line[: match.start(2)] + "[REDACTED]" + line[match.end(2) :]
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

    def python_rules(self, source: SourceFile, sha: str) -> list[FindingCandidate]:
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
                elif name.endswith(".run") and self.true_kw(node, "debug"):
                    rule = "security.debug-enabled"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if (
                    isinstance(node.value, ast.Constant)
                    and node.value.value is True
                    and any(self.name(t).lower().endswith("debug") for t in targets)
                ):
                    rule = "security.debug-enabled"
            elif isinstance(node, ast.ExceptHandler):
                if self.broad(node.type):
                    out.append(self.node("python.broad-exception", node, source, sha, lines))
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    rule = "python.empty-exception"
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
    def network(name: str) -> bool:
        parts = name.split(".")
        return (
            len(parts) > 1
            and parts[0] in {"requests", "httpx"}
            and parts[-1] in {"get", "post", "put", "patch", "delete", "head", "request"}
        )

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
    def large_file_eligible(source: SourceFile) -> bool:
        path = PurePosixPath(source.metadata.path)
        lowered_parts = tuple(part.lower() for part in path.parts)
        name = lowered_parts[-1]
        return (
            not source.metadata.is_generated
            and name not in LARGE_FILE_EXCLUDED_NAMES
            and not name.endswith(LARGE_FILE_GENERATED_SUFFIXES)
            and LARGE_FILE_EXCLUDED_DIRECTORIES.isdisjoint(lowered_parts[:-1])
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
