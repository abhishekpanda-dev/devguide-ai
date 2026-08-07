import ast
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.parser import RepositoryParseResult
from app.parser.classification import EXCLUDED_FINDINGS_CLASSIFICATIONS, classify_file
from app.parser.types import SourceFile

JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
ES_IMPORT = re.compile(
    r"^\s*import\s+(?:(?:[^;]+?)\s+from\s+)?[\"'](?P<module>[^\"']+)[\"']\s*;?\s*$"
)
ES_REEXPORT = re.compile(
    r"^\s*export\s+(?:\*|\{[^}]*\})\s+from\s+[\"'](?P<module>[^\"']+)[\"']\s*;?\s*$"
)
REQUIRE = re.compile(r"\brequire\(\s*[\"'](?P<module>[^\"']+)[\"']\s*\)")


@dataclass(frozen=True, slots=True)
class DependencyCandidate:
    source_path: str
    target_path: str
    relationship_type: str
    module_name: str
    source_line: int
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class EntryPointCandidate:
    path: str
    reason: str
    confidence: float


@dataclass(frozen=True, slots=True)
class StructureAnalysisResult:
    edges: tuple[DependencyCandidate, ...]
    entry_points: tuple[EntryPointCandidate, ...]
    limitations: tuple[str, ...] = ()


class RepositoryStructureExtractor:
    def __init__(self, *, maximum_edges: int) -> None:
        if maximum_edges < 1:
            raise ValueError("maximum_edges must be positive")
        self.maximum_edges = maximum_edges

    def analyze(self, result: RepositoryParseResult) -> StructureAnalysisResult:
        sources = {item.metadata.path: item for item in result.files}
        eligible = {
            path
            for path, source in sources.items()
            if classify_file(
                path,
                language=source.metadata.language,
                is_test=source.metadata.is_test,
                is_documentation=source.metadata.is_documentation,
                is_configuration=source.metadata.is_configuration,
                content_prefix=source.content,
            )
            not in EXCLUDED_FINDINGS_CLASSIFICATIONS
        }
        edges: list[DependencyCandidate] = []
        entries: list[EntryPointCandidate] = []
        limitations: list[str] = []
        package_json = self._package_metadata(sources.get("package.json"))
        for path in sorted(eligible):
            source = sources[path]
            if source.metadata.language == "python":
                try:
                    tree = ast.parse(source.content)
                except (SyntaxError, ValueError):
                    limitations.append(f"{path}: Python imports could not be inspected.")
                    continue
                edges.extend(self._python_edges(path, tree, eligible))
                entries.extend(self._python_entries(path, tree))
            elif source.metadata.language in {"javascript", "typescript"}:
                edges.extend(self._javascript_edges(path, source.content, eligible))
            if self._frontend_entry(path, package_json):
                entries.append(
                    EntryPointCandidate(
                        path, "Frontend bootstrap file supported by package metadata.", 0.95
                    )
                )
        entries.extend(self._package_entries(package_json, eligible))
        unique_edges = {
            (x.source_path, x.target_path, x.relationship_type, x.module_name, x.source_line): x
            for x in edges
        }
        ordered_edges = sorted(
            unique_edges.values(),
            key=lambda x: (
                x.source_path,
                x.source_line,
                x.target_path,
                x.relationship_type,
                x.module_name,
            ),
        )
        if len(ordered_edges) > self.maximum_edges:
            ordered_edges = ordered_edges[: self.maximum_edges]
            limitations.append("The configured maximum dependency edge count was reached.")
        unique_entries = {(x.path, x.reason): x for x in entries}
        return StructureAnalysisResult(
            tuple(ordered_edges),
            tuple(sorted(unique_entries.values(), key=lambda x: (x.path, x.reason))),
            tuple(sorted(set(limitations))),
        )

    def _python_edges(
        self, source_path: str, tree: ast.AST, paths: set[str]
    ) -> list[DependencyCandidate]:
        output: list[DependencyCandidate] = []
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = self._relative_python_module(source_path, node.level, node.module)
                if prefix:
                    resolved_prefix = self._resolve_python(prefix, paths)
                    children = [
                        f"{prefix}.{alias.name}" for alias in node.names if alias.name != "*"
                    ]
                    if resolved_prefix and not resolved_prefix.endswith("/__init__.py"):
                        modules = [prefix]
                    else:
                        modules = [
                            child for child in children if self._resolve_python(child, paths)
                        ] or ([prefix] if resolved_prefix else [])
            for module in modules:
                target = self._resolve_python(module, paths)
                if target and target != source_path:
                    output.append(
                        DependencyCandidate(
                            source_path,
                            target,
                            "imports",
                            module,
                            int(getattr(node, "lineno", 1)),
                        )
                    )
        return output

    @staticmethod
    def _relative_python_module(source_path: str, level: int, module: str | None) -> str:
        if level == 0:
            return module or ""
        package = list(PurePosixPath(source_path).parent.parts)
        trim = max(0, level - 1)
        if trim:
            package = package[:-trim]
        return ".".join((*package, *((module or "").split(".") if module else ())))

    @staticmethod
    def _resolve_python(module: str, paths: set[str]) -> str | None:
        base = module.replace(".", "/")
        for candidate in (f"{base}.py", f"{base}/__init__.py"):
            if candidate in paths:
                return candidate
        return None

    @staticmethod
    def _python_entries(path: str, tree: ast.AST) -> list[EntryPointCandidate]:
        entries: list[EntryPointCandidate] = []
        if PurePosixPath(path).name == "__main__.py":
            entries.append(EntryPointCandidate(path, "Python __main__.py module.", 1.0))
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and RepositoryStructureExtractor._is_main_guard(node.test):
                entries.append(EntryPointCandidate(path, "Python __name__ main guard.", 1.0))
                break
        return entries

    @staticmethod
    def _is_main_guard(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == "__name__"
            and len(node.ops) == len(node.comparators) == 1
            and isinstance(node.ops[0], ast.Eq)
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == "__main__"
        )

    def _javascript_edges(
        self, source_path: str, content: str, paths: set[str]
    ) -> list[DependencyCandidate]:
        output: list[DependencyCandidate] = []
        for number, raw_line in enumerate(content.splitlines(), 1):
            line = raw_line[:4096]
            match = ES_REEXPORT.match(line)
            relationship = "reexports" if match else "imports"
            if match is None:
                match = ES_IMPORT.match(line)
            modules: list[tuple[str, str]] = []
            if match:
                modules.append((match.group("module"), relationship))
            modules.extend(
                (item.group("module"), "requires")
                for item in REQUIRE.finditer(line)
                if self._code_position(line, item.start())
            )
            for module, relation in modules:
                target = self._resolve_javascript(source_path, module, paths)
                if target and target != source_path:
                    output.append(
                        DependencyCandidate(source_path, target, relation, module, number)
                    )
        return output

    @staticmethod
    def _code_position(line: str, position: int) -> bool:
        quote: str | None = None
        escaped = False
        index = 0
        while index < position:
            character = line[index]
            if escaped:
                escaped = False
            elif character == "\\" and quote:
                escaped = True
            elif quote:
                if character == quote:
                    quote = None
            elif character in {"'", '"', "`"}:
                quote = character
            elif character == "/" and index + 1 < position and line[index + 1] == "/":
                return False
            index += 1
        return quote is None

    @staticmethod
    def _resolve_javascript(source_path: str, module: str, paths: set[str]) -> str | None:
        if not module.startswith(".") or "\\" in module:
            return None
        base = PurePosixPath(source_path).parent.joinpath(module)
        normalized_parts: list[str] = []
        for part in base.parts:
            if part == ".":
                continue
            if part == "..":
                if not normalized_parts:
                    return None
                normalized_parts.pop()
            else:
                normalized_parts.append(part)
        normalized = "/".join(normalized_parts)
        candidates = [normalized]
        candidates.extend(f"{normalized}{extension}" for extension in JS_EXTENSIONS)
        candidates.extend(f"{normalized}/index{extension}" for extension in JS_EXTENSIONS)
        return next((candidate for candidate in candidates if candidate in paths), None)

    @staticmethod
    def _package_metadata(source: SourceFile | None) -> dict[str, object]:
        if source is None:
            return {}
        try:
            value = json.loads(source.content)
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _package_entries(metadata: dict[str, object], paths: set[str]) -> list[EntryPointCandidate]:
        output: list[EntryPointCandidate] = []
        values: list[tuple[str, str]] = []
        for field in ("main", "module"):
            value = metadata.get(field)
            if isinstance(value, str):
                values.append((value, f"package.json {field} field."))
        binary = metadata.get("bin")
        if isinstance(binary, str):
            values.append((binary, "package.json bin field."))
        elif isinstance(binary, dict):
            values.extend(
                (value, "package.json bin field.")
                for value in binary.values()
                if isinstance(value, str)
            )
        for value, reason in values:
            normalized = value.removeprefix("./")
            candidates = [normalized, *(f"{normalized}{ext}" for ext in JS_EXTENSIONS)]
            path = next((item for item in candidates if item in paths), None)
            if path:
                output.append(EntryPointCandidate(path, reason, 1.0))
        return output

    @staticmethod
    def _frontend_entry(path: str, metadata: dict[str, object]) -> bool:
        if path not in {f"src/main{extension}" for extension in JS_EXTENSIONS}:
            return False
        combined = json.dumps(metadata, sort_keys=True).casefold()
        return "vite" in combined or "react" in combined
