from enum import StrEnum


class RepositorySourceType(StrEnum):
    GITHUB_PUBLIC = "github_public"


class RepositoryStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class AnalysisJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisStageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"


class FindingCategory(StrEnum):
    MAINTAINABILITY = "maintainability"
    RELIABILITY = "reliability"
    SECURITY = "security"
