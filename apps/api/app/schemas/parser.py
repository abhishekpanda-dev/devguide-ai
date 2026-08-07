from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    repository_id: UUID
    analysis_job_id: UUID
    commit_sha: str
    path: str
    file_name: str
    extension: str
    language: str
    size_bytes: int
    line_count: int
    content_hash: str
    is_test: bool
    is_documentation: bool
    is_configuration: bool
    is_generated: bool
    encoding: str | None
    limitations: list[str]
    created_at: datetime
    updated_at: datetime


class CodeChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    repository_file_id: UUID
    analysis_job_id: UUID
    commit_sha: str
    start_line: int
    end_line: int
    content: str
    language: str
    parser_version: str
    content_hash: str
    created_at: datetime


class RepositoryParseSummary(BaseModel):
    accepted_files: int
    chunks: int
    total_bytes: int
    total_lines: int
    parser_version: str
    limitations: list[str]


class ParserPersistenceResult(BaseModel):
    repository_id: UUID
    analysis_job_id: UUID
    commit_sha: str
    files_persisted: int
    chunks_persisted: int
