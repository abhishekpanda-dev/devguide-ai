from app.findings import FindingCandidate, FindingsAnalysisResult
from app.models import FindingCategory, FindingSeverity
from app.parser.types import (
    RepositoryParseResult,
    RepositoryStatistics,
    SourceFile,
    SourceFileMetadata,
)
from app.quality import RepositoryQualityAnalyzer
from app.structure import EntryPointCandidate, StructureAnalysisResult


def source(path: str, content: str, *, test: bool = False, generated: bool = False) -> SourceFile:
    return SourceFile(
        SourceFileMetadata(
            path,
            path.rsplit("/", 1)[-1],
            ".py",
            "python",
            len(content),
            len(content.splitlines()),
            "a" * 64,
            test,
            False,
            False,
            generated,
            "utf-8",
        ),
        content,
    )


def parsed(*files: SourceFile) -> RepositoryParseResult:
    return RepositoryParseResult(
        files,
        (),
        RepositoryStatistics(
            len(files),
            len(files),
            0,
            0,
            sum(f.metadata.size_bytes for f in files),
            sum(f.metadata.line_count for f in files),
            {"python": len(files)},
            {"python": sum(f.metadata.line_count for f in files)},
            0,
            0,
            sum(f.metadata.is_test for f in files),
            files[0].metadata.path if files else None,
            files[-1].metadata.path if files else None,
            0,
            "test",
            (),
        ),
    )


BLOCK = """def calculate_total(values):
    total = 0
    for value in values:
        total = total + value
    result = total * 2
    return result
"""
ORPHAN = """def orphan_helper(value):
    adjusted = value + 1
    doubled = adjusted * 2
    squared = doubled * doubled
    return squared
"""


def test_unused_candidate_and_exact_duplicate_are_deterministic_and_bounded() -> None:
    result = RepositoryQualityAnalyzer(
        minimum_duplicate_lines=5, minimum_duplicate_tokens=10
    ).analyze(
        parsed(
            source("a.py", BLOCK),
            source("b.py", BLOCK.replace("    ", "        ")),
            source("c.py", ORPHAN),
        ),
        FindingsAnalysisResult(()),
        StructureAnalysisResult((), ()),
    )
    assert [
        (item.path, item.symbol_name, item.start_line) for item in result.unused_candidates
    ] == [("c.py", "orphan_helper", 1)]
    assert len(result.duplicate_groups) == 1
    assert result.duplicate_groups[0].group_id.startswith("dup-")
    assert result.duplicate_groups[0].confidence == 1
    assert 0 <= result.overall_score <= 100
    assert result == RepositoryQualityAnalyzer(
        minimum_duplicate_lines=5, minimum_duplicate_tokens=10
    ).analyze(
        parsed(
            source("a.py", BLOCK),
            source("b.py", BLOCK.replace("    ", "        ")),
            source("c.py", ORPHAN),
        ),
        FindingsAnalysisResult(()),
        StructureAnalysisResult((), ()),
    )


def test_referenced_entry_test_generated_and_trivial_symbols_are_excluded() -> None:
    content = "def used():\n    return 1\n\nvalue = used()\n"
    result = RepositoryQualityAnalyzer().analyze(
        parsed(
            source("main.py", content),
            source("test_x.py", BLOCK, test=True),
            source("vendor/generated.py", BLOCK, generated=True),
        ),
        FindingsAnalysisResult(()),
        StructureAnalysisResult((), (EntryPointCandidate("main.py", "main", 1),)),
    )
    assert result.unused_candidates == ()
    assert result.duplicate_groups == ()


def test_health_score_penalties_are_explainable_capped_and_reproducible() -> None:
    finding = FindingCandidate(
        "x",
        FindingSeverity.HIGH,
        FindingCategory.SECURITY,
        "x",
        "x",
        "a.py",
        1,
        1,
        "x",
        "x",
        1,
        "a" * 64,
        "b" * 40,
    )
    result = RepositoryQualityAnalyzer().analyze(
        parsed(source("a.py", "value = 1\n")),
        FindingsAnalysisResult((finding,) * 10),
        StructureAnalysisResult((), ()),
    )
    deduction = next(item for item in result.deductions if item.signal_type == "high_findings")
    assert deduction.points_deducted == 32
    assert result.category_scores["security"] == 68
    assert result.score_version == "quality-v1"
    assert 0 <= result.overall_score <= 100
