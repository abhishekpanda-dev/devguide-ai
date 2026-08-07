from pathlib import Path

from app.parser import RepositoryParser
from app.structure import RepositoryStructureExtractor, StructureAnalysisResult


def extract(root: Path) -> StructureAnalysisResult:
    return RepositoryStructureExtractor(maximum_edges=100).analyze(RepositoryParser().parse(root))


def write(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def test_python_imports_relative_resolution_lines_and_external_ignoring(tmp_path: Path) -> None:
    write(tmp_path, "app/__init__.py", "")
    write(tmp_path, "app/services.py", "value = 1\n")
    write(tmp_path, "app/util.py", "value = 2\n")
    write(
        tmp_path,
        "app/main.py",
        "import app.services\n"
        "from . import util\n"
        "from external import thing\n"
        "text = 'import app.missing'\n"
        "# import app.missing\n",
    )
    result = extract(tmp_path)
    assert [(x.target_path, x.source_line, x.module_name) for x in result.edges] == [
        ("app/services.py", 1, "app.services"),
        ("app/util.py", 2, "app.util"),
    ]


def test_javascript_and_typescript_static_resolution(tmp_path: Path) -> None:
    write(tmp_path, "src/service.ts", "export const service = 1\n")
    write(tmp_path, "src/side/index.ts", "export const side = 1\n")
    write(tmp_path, "src/util.js", "module.exports = 1\n")
    write(
        tmp_path,
        "src/main.ts",
        "import value from './service'\n"
        "import './side'\n"
        "export { value } from './service'\n"
        "const util = require('./util')\n"
        "const dynamic = require(name)\n"
        "const text = \"require('./missing')\"\n"
        "// require('./missing')\n",
    )
    result = extract(tmp_path)
    assert [(x.relationship_type, x.target_path, x.source_line) for x in result.edges] == [
        ("imports", "src/service.ts", 1),
        ("imports", "src/side/index.ts", 2),
        ("reexports", "src/service.ts", 3),
        ("requires", "src/util.js", 4),
    ]


def test_probable_python_and_package_entry_points(tmp_path: Path) -> None:
    write(tmp_path, "tool/__main__.py", "print('not executed')\n")
    write(tmp_path, "cli.py", "if __name__ == '__main__':\n    main()\n")
    write(tmp_path, "src/main.tsx", "export const app = 1\n")
    write(tmp_path, "server.js", "export const server = 1\n")
    write(
        tmp_path,
        "package.json",
        '{"main":"server.js","scripts":{"dev":"vite"},"dependencies":{"react":"latest"}}',
    )
    result = extract(tmp_path)
    entries = {(x.path, x.reason, x.confidence) for x in result.entry_points}
    assert ("tool/__main__.py", "Python __main__.py module.", 1.0) in entries
    assert ("cli.py", "Python __name__ main guard.", 1.0) in entries
    assert ("server.js", "package.json main field.", 1.0) in entries
    assert (
        "src/main.tsx",
        "Frontend bootstrap file supported by package metadata.",
        0.95,
    ) in entries


def test_edge_limit_is_stable_and_zero_edge_repository_is_supported(tmp_path: Path) -> None:
    write(tmp_path, "plain.py", "value = 1\n")
    assert extract(tmp_path).edges == ()
    write(tmp_path, "one.py", "import plain\n")
    write(tmp_path, "two.py", "import plain\n")
    result = RepositoryStructureExtractor(maximum_edges=1).analyze(
        RepositoryParser().parse(tmp_path)
    )
    assert len(result.edges) == 1
    assert result.limitations
